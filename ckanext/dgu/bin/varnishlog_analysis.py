'''
Analyse varnish logs
'''
import sys
import os
import re

from collections import defaultdict, OrderedDict

class Transaction(object):    
    def __init__(self):
        self._props = []

    def add_row_dict(self, row_dict):
        self._props.append({'type': row_dict['type'],
                            'msg': row_dict['msg'],
                            'key': row_dict.get('key'),
                            'value': row_dict.get('value')})

    @property
    def url(self):
        for prop in self._props:
            if prop['type'] == 'RxURL':
                return prop['msg']

    @property
    def hit_or_miss(self):
        for prop in self._props:
            if prop['type'] == 'TxHeader' and prop.get('key') == 'X-Varnish-Cache':
                return prop['value']

    @property
    def was_hit(self):
        hit_or_miss_str = self.hit_or_miss
        if hit_or_miss_str == None:
            return None
        return hit_or_miss_str == 'HIT'

    def get_vcl_call_response(self, vcl_call_name):
        '''
        Returns the VCL_return value following VCL_call of the the given name.
        e.g. vcl_call_name = 'recv'
        '''
        for i, prop in enumerate(self._props):
            if prop['type'] == 'VCL_call' and prop['msg'] == vcl_call_name:
                max_i = len(self._props) - 1
                vcl_recv_response = None
                while i < max_i:
                    i += 1
                    prop = self._props[i]
                    if prop['type'] == 'VCL_return':
                        return prop['msg']
                    
    @property
    def cache_reason(self):
        '''Report clues that say why the cache hit or didn\'t hit.'''
        reasons = []
        # Check response to vcl_recv
        vcl_recv_response = self.get_vcl_call_response('recv')
        if vcl_recv_response == 'pass':
            reasons.append('Varnish "pass"es on recv')
        elif vcl_recv_response == 'lookup':
            reasons.append('Varnish "lookup" in recv')

        # Check response to vcl_fetch
        vcl_recv_response = self.get_vcl_call_response('fetch')
        if vcl_recv_response and vcl_recv_response != 'deliver':
            reasons.append('Varnish "pass" on fetch')

        # Check response status code
        status = None
        for i, prop in enumerate(self._props):
            if prop['type'] == 'ObjStatus':
                status = prop['msg']
                if status[0] is not '2':
                    reasons.append('Status %s' % status)
                break
            

        # Check for HitPass - Varnish remebers that this content said it should not be cached due to Set-Cookie or ttl
        for i, prop in enumerate(self._props):
            if prop['type'] == 'HitPass':
                reasons.append('HitPass')
                break
                
        # Check for Set-Cookie (causes fetch pass)
        for i, prop in enumerate(self._props):
            if prop['type'] == 'TxHeader' and prop.get('key') == 'Set-Cookie':
                reasons.append('Set-Cookie: %s (->pass)' %
                               prop.get('value')[:10])

        # Check for cookies supplied by the user
        for i, prop in enumerate(self._props):
            if prop['type'] == 'RxHeader' and prop.get('key') == 'Cookie':
                cookies = prop.get('value').split(';')
                cookie_names = [cookie.split('=')[0].strip() for cookie in cookies]
                cookie_names = [name[:10] for name in cookie_names if name]
                reasons.append('Cookie(s): %s' % ','.join(cookie_names))

        # Check for received cache-control headers
        for i, prop in enumerate(self._props):
            if prop['type'] == 'RxHeader' and prop.get('key') == 'Cache-Control':
                reasons.append('Browser cache-control: %s' % prop.get('value'))

        # Check for returned cache-control headers
        for i, prop in enumerate(self._props):
            if prop['type'] == 'TxHeader' and prop.get('key') == 'Cache-Control':
                reasons.append('Returned cache-control: %s' % prop.get('value'))

        return ', '.join(reasons) or '(no reason)'

def analyse(vlog_filepath, cmd, args):
    # Parse log and populate transactions dict (of open transactions)
    open_transactions_dict = {} # transation_id: transaction_dict
    transactions = []
    with open(vlog_filepath, 'r') as f:
        line_count = 0
        while True:
            row = f.readline()
            if row == '':
                # end of file
                break
            line_count +=1 
            row_dict = parse_row(row)
            id = row_dict['transaction_id']                
            if row_dict['type'] == 'ReqEnd' and id in open_transactions_dict:
                transaction = open_transactions_dict[id]
                transactions.append(transaction)
                del open_transactions_dict[id]
            if row_dict['type'] == 'ReqStart':
                open_transactions_dict[id] = Transaction()
                open_transactions_dict[id].line = line_count
                open_transactions_dict[id].id = id
            if id in open_transactions_dict:
                open_transactions_dict[id].add_row_dict(row_dict)

    if cmd == 'list':
        print 'List of transactions\n'
        for transaction in transactions:
            print transaction.line, transaction.url, transaction.was_hit

    elif cmd == 'urls':
        print 'Top URLs\n'
        transactions_by_url = defaultdict(list)
        for transaction in transactions:
            transactions_by_url[transaction.url].append(transaction)
        print "Reqs, Hits, URL, Log line number of ReqStart, Miss reason"
        for url, t_list in sorted(transactions_by_url.items(),
                                  key=lambda t: len(t[1]), reverse=True)[:50]:
            hits = sum([1 if t.was_hit else 0 for t in t_list])
            hit_percent = int(float(hits)/len(t_list)*100)
            miss_reason = ''
            if hit_percent < 100:
                for t in t_list:
                    if not t.was_hit:
                        miss_reason = t.cache_reason
            print len(t_list), '%s%%' % hit_percent, url, \
                  ','.join([str(t.line) for t in t_list][:5]), \
                  miss_reason
            print

    elif cmd == 'url':
        url = args[0]
        url_re = re.compile(url)
        print 'URL: %s\n' % url
        matches = 0
        for t in transactions:
            if url_re.match(t.url):
                matches += 1
                print t.line, t.hit_or_miss, t.url, t.cache_reason
                print
        print '%i matches' % matches

    elif cmd == 'summary':
        print 'Summary\n'
        print 'Requests:', len(transactions)
        hits = misses = 0
        for t in transactions:
            if t.was_hit:
                hits += 1
            else:
                misses += 1
        print 'Hits:', float(hits)/(hits+misses)*100, '%'

def parse_row(row_str):
    row = {}
    row['transaction_id'] = int(row_str[:5])
    row['type'] = row_str[5:18].strip()
    #row['side'] =  row_str[18:19] # 'b' means "backend transaction, and 'c' client side transaction.
    row['msg'] = row_str[21:].strip()
    if ':' in row['msg']:
        colon_pos = row['msg'].find(':')
        row['key'] = row['msg'][:colon_pos]
        row['value'] = row['msg'][colon_pos+2:]
    return row
    
if __name__ == '__main__':
    USAGE = '''Analyse varnish logs
    Usage: python %s <vlog.txt> <command>
    Where <command> is:
        summary - overall stats
        list  - lists details of transactions
        urls   - top urls
        url <url>  - list details of one particular url (regular exp)
    ''' % sys.argv[0]
    if len(sys.argv) < 3 or sys.argv[1] in ('--help', '-h'):
        err = ''
        if len(sys.argv) < 2:
            err = 'Error: Please specify varnish log filepath.'
        elif len(sys.argv) < 3:
            err = 'Error: Please specify command.'
        print USAGE, err
        sys.exit(1)
    vlog_file = sys.argv[1]
    vlog_filepath = os.path.abspath(vlog_file)
    command = sys.argv[2]
    args = sys.argv[3:] if len(sys.argv) > 3 else []

    analyse(vlog_filepath, command, args)
