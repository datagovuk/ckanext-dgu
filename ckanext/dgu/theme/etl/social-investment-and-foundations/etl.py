#!/usr/bin/env python
# coding=UTF-8

import pandas
import json
import sys
import os

# --------------------------------------------------------------------------------

_errors = []
_warnings = []
_info = []

def error(string):
    _errors.append(string)
def warn(string):
    _warnings.append(string)
def info(string):
    _info.append(string)

def extract(csv_filename):
    raw = pandas.read_csv(csv_filename, header=0)
    # Create a clean dataframe
    df = pandas.DataFrame()
    df['date'] = raw['Investment Commitment Date'].map( pandas.to_datetime )
    # df['date2'] = raw[u'Investment Draw Down Date']
    # df['date3'] = raw[u'Scheduled Redemption Date']
    # df['cash misleading'] = raw[u'Amount Guaranteed']
    df['invested'] = raw[u'Cash Invested']
    df['coinvestment'] = raw[u'Total Value']
    # df['written off'] = raw[u'Written Off']
    # df['payment_freq'] = raw[u'Payment Frequency']
    # df['is_bullet'] = raw[u'Bullet Payment']
    # df['is_balloon'] = raw[u'Balloon Payment']
    df['product type'] = raw[u'Product Type']
    df['purpose'] = raw[u'Purpose Of Investment']
    df['source postcode'] = raw[u'Source Of Investment']
    # df['target1'] = raw[u'Location Of Investee']
    # df['target2'] = raw[u'Geography Of Beneficiaries']
    df['sector'] = raw[u'Sector']
    df['target type'] = raw[u'Type Of Organisation Invested In']
    # df['charity number'] = raw[u'Charity Number']
    # df['company number'] = raw[u'Company Number']
    df['foundation'] = raw[u'Foundation Name']
    assert sorted(df['foundation'].unique())==['BARROW CADBURY','LANKELLYCHASE','PANAHPUR'], df['foundation']
    return df

# Utility function used below...
def get_subframe(frame,year=None,foundation=None):
    if year is not None:
        frame = frame[ frame['date'].map(lambda x:x.year==year) ]
    if foundation is not None:
        frame = frame[ frame['foundation']==foundation ]
    return frame

def global_sectors(df):
    # Ordered list of sectors is used across multiple charts
    return df.groupby(['sector']).invested.sum().order().index

def transform_barchart(df):
    # RENDER STACKED BAR CHART. Data structure for a chart:
    # { legend: ['foo','bar'...],
    #   series: [ {'major':2010, 'elements':[{'name':'foo','value':123...},...] },
    #             {'major':2010, 'elements':[{'name':'foo','value':456...},...] }, ... ]
    def pandas_barchart(frame):
        out = { 'legend' : list(global_sectors(df)), 'series': [] }
        for year in [2010,2011,2012,2013]:
            tmp = get_subframe(frame,year=year)\
                .groupby(['sector'])\
                .invested.sum()\
                .reindex(index=global_sectors(df),fill_value=0)
            elements = [ {'name':x,'value':y} for (x,y) in tmp.iteritems() ]
            out['series'].append({'major':year, 'elements':elements})
        return out
    barchart = {
        'all'                 : pandas_barchart(df),
        'foundation_panahpur' : pandas_barchart(get_subframe(df,foundation='PANAHPUR')),
        'foundation_lankelly' : pandas_barchart(get_subframe(df,foundation='LANKELLYCHASE')),
        'foundation_barrow'   : pandas_barchart(get_subframe(df,foundation='BARROW CADBURY')),
    }
    return barchart

def transform_pie1(df):
    # RENDER PIE CHART. Data structure for a chart:
    # [{'name':'foo','value':123}, {'name'...} ...]
    # -- pie1 draws the sector total values
    def pandas_pie1(frame):
        tmp = frame.groupby(['sector'])\
            .invested.sum()\
            .reindex(index=global_sectors(df),fill_value=0)
        return [ {'name':x,'value':y} for (x,y) in tmp.iteritems() ]
    pie1 = {
        'all'                 : pandas_pie1(df),
        'foundation_panahpur' : pandas_pie1(get_subframe(df,foundation='PANAHPUR')),
        'foundation_lankelly' : pandas_pie1(get_subframe(df,foundation='LANKELLYCHASE')),
        'foundation_barrow'   : pandas_pie1(get_subframe(df,foundation='BARROW CADBURY')),
    }
    return pie1
    
def transform_pie2(df):
    # RENDER ANOTHER PIE CHART. Data structure for a chart:
    # [{'name':'foo','value':123}, {'name'...} ...]
    # -- pie2 draws the secured vs unsecured product types
    legend_pie2 = df.groupby(['product type']).invested.sum().order().index.tolist()
    # Deliberately re-order the legend to give a better graph. Secured things go first.
    for x in ['Loans and facilities - Partially secured','Loans and facilities - Unsecured']:
        legend_pie2.remove(x)
        legend_pie2.insert(0,x)
    # --
    def pandas_pie2(frame):
        tmp = frame.groupby(['product type'])\
            .invested.sum()\
            .reindex(index=legend_pie2,fill_value=0)
        return [ {'name':x,'value':y} for (x,y) in tmp.iteritems() ]
    pie2 = {
        'all'                 : pandas_pie2(df),
        'foundation_panahpur' : pandas_pie2(get_subframe(df,foundation='PANAHPUR')),
        'foundation_lankelly' : pandas_pie2(get_subframe(df,foundation='LANKELLYCHASE')),
        'foundation_barrow'   : pandas_pie2(get_subframe(df,foundation='BARROW CADBURY')),
    }
    return pie2
    
def transform_sankey(df):
    # DRAW A SANKEY DIAGRAM:
    # Connecting:  target type  ->  product type  ->  purpose  -> sector
    # --------
    # Front-end data structure expectation:
    # {"nodes":[  {"name":"Agricultural 'waste'"},... ],
    #  "links":[  {"source":0,"target":1,"value":124.729,foundationSplit:[['Panahpur',9999]...]}, ..]}
    # --------
    # List of all unique values. Their index is their unique ID on the client.
    sankey_nodes = pandas.concat([ 
                      df['target type'],
                      df['product type'],
                      df['purpose'],
                      df['sector'] 
                  ]).unique()
    sankey_get_index = {value:index for (index,value) in enumerate(sankey_nodes)}
    # List of links to render. Indexes into sankey_nodes. foundationSplit = [ ['name',1234],['name2',5678] ]
    def create_links(left,right):
        for (leftval,rightval),group in df.groupby([left,right]):
            subseries = group.groupby('foundation').invested.sum()
            # Each group is a link on the sankey chart
            yield {     'source':sankey_get_index[leftval],
                        'target':sankey_get_index[rightval],
                        'value' :group.invested.sum(),
                        'foundationSplit' : sorted(subseries.to_dict().items())
                  }
    sankey = {  
        'nodes': [{'name':x} for x in sankey_nodes], 
        'links': list(create_links('target type','product type'))\
                 + list(create_links('product type','purpose'))\
                 + list(create_links('purpose','sector'))
    }
    return sankey

def transform_sunburst(df):
    # RENDER A SUNBURST. Data structure is recursive:
    # { 'name':'root', 'children': [ 
    #      { 'name':'foo', 'value':123 },
    #      { 'name':'bar', 'value':456, 'children'=[...] }, ... ] }
    # -- Group investments by coinvestment.
    # Algorithm matches on the 'total investment' column.
    sunburst = {'name':'Coinvestment','children':[]}
    for (coinvestment),group in df.groupby(['coinvestment']):
        children = group.groupby('foundation').invested.sum()
        if len(children)==1 and children.sum()>=coinvestment:
            # Simple major segment
            (name,value) = children.to_dict().items()[0]
            if value!=coinvestment:
                warn("%s has investment of %d but coinvestment of %d" % (name,value,coinvestment))
            sunburst['children'].append({ 'name':name,'size':value })
        else:
            # Complex major segment with children
            entry = {'name':'Total Investment', 'size':coinvestment, 'children':[]}
            sunburst['children'].append(entry)
            for (name,value) in children.iteritems():
                entry['children'].append( {'name':name,'size':value} )
            entry['children'].append( {'name':'(others)', 'size':coinvestment - children.sum()} )
    return sunburst

def transform_total(df):
    investment_total = {
        'all'                 : df['invested'].sum(),
        'foundation_panahpur' : get_subframe(df,foundation='PANAHPUR')['invested'].sum(),
        'foundation_lankelly' : get_subframe(df,foundation='LANKELLYCHASE')['invested'].sum(),
        'foundation_barrow'   : get_subframe(df,foundation='BARROW CADBURY')['invested'].sum(),
    }
    return investment_total


def main():
    infile = "data.csv"
    outfile = "../../src/scripts/json/social-investment-and-foundations.json"
    assert os.path.exists(infile),"Input file does not exist: "+infile
    assert infile.endswith('.csv'),"Expected input file with extension 'csv'"
    assert outfile.endswith('.json'),"Expected output file with extension 'json'"
    data = extract(infile)
    # EXPORT: Write to file
    graphs = {
          'bar' : transform_barchart(data),
          'pie1' : transform_pie1(data),
          'pie2' : transform_pie2(data),
          'sankey' : transform_sankey(data),
          'sunburst' : transform_sunburst(data),
          'coinvestment_total' : data['coinvestment'].unique().sum(),
          'investment_total' : transform_total(data),
      }
    print json.dumps({"errors": _errors, "warnings": _warnings, "info" : _info }, indent=4)
    if len(_errors):
        sys.exit(-1)
    with open(outfile,'w') as f:
        json.dump(graphs,f)

if __name__=='__main__':
    main()
