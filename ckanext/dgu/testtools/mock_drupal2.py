# -*- coding: latin-1 -*-
import logging

from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.lib.base import BaseController, render
from ckan.lib.base import response
from ckan.lib.helpers import json

log = logging.getLogger(__name__)

class MockDrupal2(SingletonPlugin):

    implements(IRoutes, inherit=True)

    def before_map(self, map):
        map.connect('/comment/get/{id}', controller='ckanext.dgu.testtools.mock_drupal2:MockDrupal2Controller', action='get_comments_html')
        map.connect('/comment/get/{id}/json', controller='ckanext.dgu.testtools.mock_drupal2:MockDrupal2Controller', action='get_comments_json')
        map.connect('/comment/dataset/{id}', controller='ckanext.dgu.testtools.mock_drupal2:MockDrupal2Controller', action='add_comment')
        return map

class MockDrupal2Controller(BaseController):
    comments = {}
    def get_comments_json(self, id):
        if id not in self.comments:
            self.comments[id] = example_comments_json
        comments = self.comments[id]
        response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        log.info('GET Comments (json)')
        return json.dumps(comments)

    def get_comments_html(self, id):
        if id not in self.comments:
            self.comments[id] = example_comments_html
        comments = self.comments[id]
        log.info('GET Comments (html)')
        return comments

    def add_comment(self, id):
        return 'Add a comment form'


example_comments_json = [{"cid":"2135","pid":"0","nid":"9556","subject":"Great to see this data","comment":"Great to see this data released","format":"1","timestamp":"1275641166","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"01\/","status":"0","children":[{"cid":"2205","pid":"2135","nid":"9556","subject":"Well done","comment":"Great to see this being released and shared by P2P. Well done, many more steps in this direction needed.","format":"1","timestamp":"1275676408","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"01.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2205"},{"cid":"2228","pid":"2135","nid":"9556","subject":"I agree","comment":"it is good to see this released - yes it will take time for people to make sense of it all and yes it is just one of a large number of steps needed to make the UK Government more transparent but it is a welcome step.","format":"1","timestamp":"1275818482","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"01.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2228"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2135"},{"cid":"2136","pid":"0","nid":"9556","subject":"Format of the data?","comment":"What id the format of the data please?","format":"1","timestamp":"1275641569","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02\/","status":"0","children":[{"cid":"2137","pid":"2136","nid":"9556","subject":"Understanding the COINS data","comment":"A document is available at\r\n http:\/\/www.hm-treasury.gov.uk\/d\/coins_guidance_040610.pdf","format":"1","timestamp":"1275646662","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2137"},{"cid":"2139","pid":"2136","nid":"9556","subject":"Data details","comment":"The data is described here\r\n\r\nhttp:\/\/www.hm-treasury.gov.uk\/d\/coins_guidance_040610.pdf","format":"1","timestamp":"1275647257","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2139"},{"cid":"2140","pid":"2136","nid":"9556","subject":"csv","comment":"it is in csv format\r\n\r\nimport it into a database as csv","format":"1","timestamp":"1275646025","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2140"},{"cid":"2143","pid":"2136","nid":"9556","subject":"Comma separated values","comment":"By the look of it - they are all named xxxx.csv and have a matching icon.","format":"1","timestamp":"1275646330","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.03\/","status":"0","reply_url":"\/comment\/reply\/9556\/2143"},{"cid":"2146","pid":"2136","nid":"9556","subject":"CSV means comma separated values","comment":"CSV means comma separated values, therefore each field (or column) of data will have a comma to separate it from the next one. this is a very common format and it can be directly imported into Office\'s Excel, iWork\'s Numbers or OpenOffice.org\'s Calc but\r\ngiven that the dataset is rather large, it would be wiser to import it into a Oracle or similar database...","format":"1","timestamp":"1275648510","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.04\/","status":"0","reply_url":"\/comment\/reply\/9556\/2146"},{"cid":"2160","pid":"2136","nid":"9556","subject":"txt","comment":"eg. \r\nfact_table_extract_2009_10.zip  -\u003e fact_table_extract_2009_10.txt","format":"1","timestamp":"1275652676","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.05\/","status":"0","reply_url":"\/comment\/reply\/9556\/2160"},{"cid":"2166","pid":"2136","nid":"9556","subject":"Data format...","comment":"Looks to be @-delimited rather than CSV. File also includes some notes in lenes beneath the table - likely these need cleaning in a text editor before putting into something like Excel.\r\n\r\nPresumably all this is to help ensure no one can use this easily?","format":"1","timestamp":"1275654669","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"02.08\/","status":"0","reply_url":"\/comment\/reply\/9556\/2166"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2136"},{"cid":"2141","pid":"0","nid":"9556","subject":"Slice the data","comment":"Because it's too big for people's machines, can you slice the data by date or department?","format":"1","timestamp":"1275647600","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"03\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2141"},{"cid":"2142","pid":"0","nid":"9556","subject":"Extracted size","comment":"Crikey - 4GB uncompressed each! - thats a lot of data to wade through..","format":"1","timestamp":"1275647902","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"04\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2142"},{"cid":"2144","pid":"0","nid":"9556","subject":"Brilliant","comment":"Glad to see Labour\'s waste exposed.\r\n\r\nNow maybe the public can see where their money is being spent.","format":"1","timestamp":"1275648082","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"05\/","status":"0","children":[{"cid":"2171","pid":"2144","nid":"9556","subject":"Re: Brilliant","comment":"\"Labour\'s Waste\" - seems like you\'ve made your mind up before you\'ve even looked at the data","format":"1","timestamp":"1275656998","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"05.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2171"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2144"},{"cid":"2145","pid":"0","nid":"9556","subject":"well done for the additional Torrent format","comment":"I think it\'s been a wise choice to distribute the files also through the Torrent method","format":"1","timestamp":"1275648106","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"06\/","status":"0","children":[{"cid":"2169","pid":"2145","nid":"9556","subject":"BitTorrent","comment":"It\'s good to see BitTorrent being used for its true purposes, disseminating large amounts of data efficiently with low server loads. Hopefully an increasing trend in legitimate and official use of Torrenting in this way will help to break down BitTorrent\'s poor reputation for legality.\r\n\r\nWhichever manager stepped back and allowed the geeks to be in charge of releasing this data set deserves to be commended!","format":"1","timestamp":"1275656351","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"06.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2169"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2145"},{"cid":"2148","pid":"0","nid":"9556","subject":"COIN Downloads","comment":"Why make the files so large that most people cannot easily view them!","format":"1","timestamp":"1275649169","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"07\/","status":"0","children":[{"cid":"2153","pid":"2148","nid":"9556","subject":"Why make the files so large?","comment":"Quite simply, because there is a lot of data.\r\n\r\nThey did not \"make the files large\" - the files ARE large, due to the amount of data in them.\r\n\r\n","format":"1","timestamp":"1275648348","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"07.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2153"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2148"},{"cid":"2149","pid":"0","nid":"9556","subject":"About time this information","comment":"About time this information was made available?","format":"1","timestamp":"1275649149","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"08\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2149"},{"cid":"2150","pid":"0","nid":"9556","subject":"Good and not so good","comment":"Great to see this data released, and well done for getting out so quickly. Shame that on a subject of trnasparancy and openess, very few people will be able to access the data. May I suggest that the files be broken down into smaller more managable downloads and an index be provided?","format":"1","timestamp":"1275649744","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"09\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2150"},{"cid":"2151","pid":"0","nid":"9556","subject":"Data Format","comment":"It would be helpful to present the data in a user friendly format for the general public to access.  \r\n\r\nBreaking down the files by department, year and month would be much more manageable.   ","format":"1","timestamp":"1275649785","name":"mhayworth","mail":"mhayworth@btinternet.com","homepage":"","uid":"3611","registered_name":"mhayworth","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-6895b9b6915e2ed02321e2d2147c56ef\";s:9:\"conf_mail\";s:24:\"mhayworth@btinternet.com\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1275648461-100604f9b402697bd7\";s:7:\"captcha\";s:5:\"FSZ1f\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"0a\/","status":"0","children":[{"cid":"2184","pid":"2151","nid":"9556","subject":"Breaking down the files by department","comment":"Unfortunately, some lines of data relate to transfers from one Department to another, so, breaking down the files by department would mean that such transfers would need to be presented twice.\r\n\r\nI think that Treasury only undertook to publish the raw data, but not to provide an analysis tool (such as drill-down webpages).  And, as they acknowledge, to provide any meaningful analsysis will require a high level of expertise.\r\n\r\nAnonorak\r\n\r\n","format":"1","timestamp":"1275657391","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0a.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2184"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2151"},{"cid":"2154","pid":"0","nid":"9556","subject":"Corrupted zip file","comment":"The 2009-10 zip file won\'t extract - says file is corrupted. Anyone else getting this error?","format":"1","timestamp":"1275650234","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0c\/","status":"0","children":[{"cid":"2161","pid":"2154","nid":"9556","subject":"extract zip","comment":"Don\'t depend on XP ect  only ! Use Ubuntu etc. , then no problem","format":"1","timestamp":"1275652741","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0c.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2161"},{"cid":"2179","pid":"2154","nid":"9556","subject":"Corrupted file","comment":"I see the same.  Download was successful but the file is .txt file, not a .csv file.  Maybe it is too large for the default opening programme Notepad.","format":"1","timestamp":"1275656460","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0c.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2179"},{"cid":"2180","pid":"2154","nid":"9556","subject":"corrupt file","comment":"Yes, I get a corrupt file message as well.\r\n\r\nJohn Bradford","format":"1","timestamp":"1275658172","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0c.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2180"},{"cid":"2191","pid":"2154","nid":"9556","subject":"corrupted zip file","comment":"I also had the message that the zip file was corrupted - I then gave up. But the following links tell you how to open torrent files - i haven\'t tried it.\r\n\r\nhttp:\/\/www.associatedcontent.com\/article\/477663\/how_to_open_a_torrent_file.html?cat=15\r\n\r\n\r\nhttp:\/\/www.bittorrent.com\/\r\n","format":"1","timestamp":"1275662266","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0c.03\/","status":"0","reply_url":"\/comment\/reply\/9556\/2191"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2154"},{"cid":"2156","pid":"0","nid":"9556","subject":"PHP Parsing UTF16","comment":"The data can be imported using PHP if you play a trick to change the converting from UTF16 to ASCII by eliminating every 2nd byte.\r\n\r\nUse fgets on the main file in x64 mode to bypass the 4GB boundary .\r\n\r\nPlease excuse the absolutely horrible hack-up job. http:\/\/utilitybase.com\/paste\/33282","format":"1","timestamp":"1275650801","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0d\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2156"},{"cid":"2157","pid":"0","nid":"9556","subject":"Interesting that the data is","comment":"Interesting that the data is downloadable via a torrent considering the problems such services cause via copyright infringement.","format":"1","timestamp":"1275650946","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0e\/","status":"0","children":[{"cid":"2176","pid":"2157","nid":"9556","subject":"Torrents","comment":"Torrents are not \"burglars\' tools\" - they are a perfectly normal distribution method for large files. For example, many Linux operating systems are distributed via torrrent. Torrents have the additional feature of allowing altruists to take a share of the hosting costs for the further distribution of files they themselves have downloaded. To have data available from this site is a very positive thing.","format":"1","timestamp":"1275657607","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0e.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2176"},{"cid":"2186","pid":"2157","nid":"9556","subject":"its also a hugely effective","comment":"its also a hugely effective way of distributing large files, which actually speeds up when a file is popular, unlike a traditional client-server transfer which would slow down, plus it cuts down the bandwidth cost of serving the data, so surely its a good thing all round?","format":"1","timestamp":"1275659398","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0e.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2186"},{"cid":"2189","pid":"2157","nid":"9556","subject":"Torrents","comment":"Torrents are just a technology, it is not inherently linked to copyright infringement. It\'s like saying \'Interesting that this is available on the Internet, where there is lots of porn too.\' Perhaps true, but not really of any point.","format":"1","timestamp":"1275659910","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0e.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2189"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2157"},{"cid":"2158","pid":"0","nid":"9556","subject":"Why the hell isnt the data","comment":"Why the hell isnt the data stored centrally in a database with webpages drilling into it?  Most ppl dont know what to do with a csv file.\r\n\r\nSurely if you going to go to the effort of publishing then do it properly so that non technical people actually do have access.","format":"1","timestamp":"1275651183","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0f\/","status":"0","children":[{"cid":"2193","pid":"2158","nid":"9556","subject":"Having the data yourself","comment":"Having the data yourself means that no-one can claim the govt is preventing you finding facts.  Also, these services will spring up as interested parties analyse the data, and they\'ll be independent.  Much more sensible this way, I\'d say.","format":"1","timestamp":"1275663139","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0f.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2193"},{"cid":"2232","pid":"2158","nid":"9556","subject":"How far should they really go?","comment":"I can open it fine, with a bit of trial and error.\r\n\r\nTry microsoft website, download the free version of sql server \u0026 import the data. easy peasy.\r\n\r\nI\'m all for freedom of information, but I\'d be annoyed if the govt then spent millions at inflated rates for some contractor\/fms company to come in \u0026 make it \"easy\" for all to browse at their leisure. Importing this data is far simpler than trying to make some meaning of it. Think about it.\r\n","format":"1","timestamp":"1275852264","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0f.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2232"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2158"},{"cid":"2159","pid":"0","nid":"9556","subject":"How to unzip","comment":"Please list successful solutions for Windows XP and Linuz (Debian Etch)\r\n\r\nI have tried several programs on both OS and non-succeed (e.g. on fact 2010)\r\n\r\nThanks\r\n\r\nMark","format":"1","timestamp":"1275651582","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0g\/","status":"0","children":[{"cid":"2217","pid":"2159","nid":"9556","subject":"How to unzip","comment":"PKZIP works.\r\nThe file unzips as a .txt file, not .csv, so I simply changed the filename to .csv and opened it in Excel 2010, which asked for the delimiter, which is @ (not comma).  Then it works.\r\n\r\nExcept that Excel 2010 has \'only\' about 1,000,000 rows, which isn\'t nearly enough.  In fact the data that did download is about 50% nil values.\r\n\r\nHow to open the remainder of the file? I don\'t know.","format":"1","timestamp":"1275688685","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0g.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2217"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2159"},{"cid":"2167","pid":"0","nid":"9556","subject":"I downloaded the file but as","comment":"I downloaded the file but as I am no computer whizz I have been unable to find out how to open it.  Why have you made it so complicated?  I normally use Adobe and beyond that I am out of my depth.","format":"1","timestamp":"1275653882","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0i\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2167"},{"cid":"2168","pid":"0","nid":"9556","subject":"Unable to open","comment":"Typical Tory duplicity - how the hell is an ordinary person meant to open this. ","format":"1","timestamp":"1275655993","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0j\/","status":"0","children":[{"cid":"2221","pid":"2168","nid":"9556","subject":"Try the user interface","comment":"Try the user interface provided by the guardian newspaper\r\n\r\ngeoff","format":"1","timestamp":"1275735763","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0j.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2221"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2168"},{"cid":"2170","pid":"0","nid":"9556","subject":"Mac problems?","comment":"It seems the out of the box unarchiver on OSX can\'t deal with large files, such as the COINS fact table. It spits out a cpgz file, which if you try to unzip just creates another zip, and so on, and so on.\r\n\r\nThankfully I managed to unzip it using Keka (http:\/\/www.kekaosx.com\/en\/), which is an OSX form of 7zip. This worked without any problems. Just thought I\'d share in case anyone else was having any difficulties.\r\n","format":"1","timestamp":"1275656676","name":"pezholio","mail":"pezholio@gmail.com","homepage":"","uid":"42","registered_name":"pezholio","signature":"","signature_format":"0","picture":"","data":"a:4:{s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";s:13:\"form_build_id\";s:37:\"form-2eea13b3425250fb9e78e81a720d1bde\";}","thread":"0k\/","status":"0","children":[{"cid":"7695","pid":"2170","nid":"9556","subject":"keka","comment":"\u003cp\u003eThanks for this. \u0026nbsp;I hadn\'t tried it yet but have no doubt I would have had the same problems.\u003c\/p\u003e","format":"6","timestamp":"1323818230","name":"Anonymous","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0k.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/7695"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2170"},{"cid":"2173","pid":"0","nid":"9556","subject":"COINS contains millions of","comment":"COINS contains millions of rows of data; as a consequence the files are large and the data held within the files complex.  Using these download files will require some degree of technical competence and expertise in handling and manipulating large volumes of data.  It is likely that these data will be most easily used by organisations that have the relevant expertise, rather than by individuals. By having access to these data, institutions and experts will be able to process and present them in a way that is more accessible to the general public. In addition, subsets of data from the COINS database will also be made available in more accessible formats by August 2010.\r\n\r\n\r\n","format":"1","timestamp":"1275657120","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0m\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2173"},{"cid":"2174","pid":"0","nid":"9556","subject":"Checksum for 2009\/10 zip file","comment":"sha1sum fact_table_extract_2009_10.zip \r\nc163e7e1fba578e38bb3cf295bd1be0514d2fcf9  fact_table_extract_2009_10.zip\r\n\r\nCorrupt on unzipping. Does anyone else get a different sha1sum checksum for this file?","format":"1","timestamp":"1275657232","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0n\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2174"},{"cid":"2175","pid":"0","nid":"9556","subject":"Is this CSV?","comment":"I unzipped the (non-torrent) version of the 09\/10 adjustment table and it wasn\'t CSV but rather 2-sign delimited (think tab-delim with an @ instead of a tab). also the data wasn\'t clean for import to something like Excel as it had some lines of non-table data at the end - just the sort of thing to upset already hard-pushed spreadsheet importers on non-high end rigs.","format":"1","timestamp":"1275657527","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0o\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2175"},{"cid":"2178","pid":"0","nid":"9556","subject":"Making the Data Accessible","comment":"Please provide this data in a form that can be drilled down from within a browser. \r\n\r\nYou get a tick for making the data available, but loose points for inaccessibility!","format":"1","timestamp":"1275657830","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0p\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2178"},{"cid":"2182","pid":"0","nid":"9556","subject":"Formatting","comment":"Could whomever is responsible for creating these files please give it another go with the following:\r\n\r\n1. Use UTF-8 or ASCII instead of UTF-8 - Almost half this file is empty space!\r\n2. Use proper CSV, double quoted where needed\r\n3. Compress to RAR\r\n4. Replace NONE with an empty field.\r\n\r\nI\'ve just done it here on my side and been able to reduce the 09-10 file down from the original 4 GB to 1.8GB, 23MB RAR - which is small enough to open in Excel if you\'ve got 6+ GB of RAM installed.\r\n\r\n- Mark Randall","format":"1","timestamp":"1275658152","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0q\/","status":"0","children":[{"cid":"2198","pid":"2182","nid":"9556","subject":"sorry Mark...","comment":"...it\'s not the number of bytes that\'s important here but the number of records (rows). We all know that we can reduce the number of fields (columns) as many are redundant and others are irrelevant, but 2+ mln records are too many for Xls, also if you have just two fields. I can open the entire 4Gb in Xls but before visualize the content I\'m told not the entire file would be open...","format":"1","timestamp":"1275667234","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0q.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2198"},{"cid":"2213","pid":"2182","nid":"9556","subject":"RAR is inappropriate","comment":"As it is a secret, proprietary format which cannot be opened with free software.","format":"1","timestamp":"1275685022","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0q.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2213"},{"cid":"2222","pid":"2182","nid":"9556","subject":"Re: Formatting","comment":"3. Compress to RAR\r\n\r\nRight, you want open and transparent data that\'s compressed using a proprietary algorithm. Isn\'t that defeating the purpose? Not to mention, PPMd and LZMA (as implemented by 7-zip) have generally yielded higher compression ratios than RAR\'s proprietary mess.\r\n\r\nNot to mention that any RAR files created would be wholly illegal unless someone paid for WinRAR. No such restriction on 7-zip and it\'s technologies.\r\n\r\nFrom the WinRAR license:\r\n\r\n   8. There are no additional license fees, \u003cstrong\u003eapart from the cost of purchasing a license\u003c\/strong\u003e, associated with the creation and distribution of RAR archives, volumes, self-extracting archives or self-extracting volumes. Legally registered owners may use their copies of RAR\/WinRAR to produce archives and self-extracting archives and to distribute those archives free of any additional RAR royalties.\r\n\r\nIn short, you must pay for a license before you can distribute archives. The whole purpose of opening up this dataset is to allow anyone to audit the government\'s spending, with the goal of reducing wasteful spending. Paying for WinRAR when superior and free alternatives exist is just more wasteful spending.","format":"1","timestamp":"1275737996","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0q.02\/","status":"0","reply_url":"\/comment\/reply\/9556\/2222"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2182"},{"cid":"2187","pid":"0","nid":"9556","subject":"addressing some concerns","comment":"to all the people who are commenting that the information is being released in a difficult to consume form, this is GOOD. this is what we really need, the RAW data. if it were sliced up into easier to consume packages, or presented in nice webpages, it would just mean the civil service taking us further away from the raw original data in the form it was produced, further from the truth basically.\r\n\r\nnow that the raw data has been released, hacker types (in the traditional sense) the world over can dig through it and present it in any form they\/you want. in the coming weeks months and years you will start to see other websites where you will be able to browse, consume and interpret the data in every form imaginable, from traditional spreadsheet style interfaces to insane hollywood style 3d topographical visualisations. these will be built by citizens, using the raw data finally releaed here by government. this page and these csv files are meant for consumption by these hackers, if they were put into a form easily understandable\/consumable by the general public this would completely defeat the point of the exercise.\r\n\r\nright, off to hack some code! ive been looking for a data set to feed into those python machine learning algorithms they taught us at uni...","format":"1","timestamp":"1275659443","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0s\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2187"},{"cid":"2188","pid":"0","nid":"9556","subject":"Corrupt zip file ?","comment":"Zipped 2009\/10 Fact table, 67MiB (4.28GiB uncompressed) is coming up as corrupt when I try and extract the contents.","format":"1","timestamp":"1275659707","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0t\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2188"},{"cid":"2190","pid":"0","nid":"9556","subject":"Good Choice","comment":"I\'m glad to see this data available, and shared in such a format that allows for easy analysis.\r\n\r\nThe choice of sharing medium (bittorrent) is also a good choice. It allows large files to be shared while reduce load on the host server, and therefore lowering the necessary server costs saving tax payer money. In theory at least.\r\n\r\nThank you.","format":"1","timestamp":"1275661826","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0u\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2190"},{"cid":"2194","pid":"0","nid":"9556","subject":"The Plan","comment":"To those complaining about the format and size of the data....\r\n\r\nThe new government has stated that they expect the digesting, analysis and redistribution of this data to be conducted by 3rd parties. These 3rd parties, who are willing to put money into making the data more readable and then potentially sell it on, are the ones who are more likely to download and use the data in it\'s current form.","format":"1","timestamp":"1275663617","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0v\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2194"},{"cid":"2199","pid":"0","nid":"9556","subject":"another concern","comment":"I do not want to complain on the weight or the format of the data, but it seems to me that this is just a query from a database and nobody did care about the quality after it (who uses @ as a separation element?!?!. the most difficult thing is not importing the data in this or that system but controlling that everything is correct because a few records do not import in the right shape. however, I really enjoy reading this sentence from the guidance booklet \"Therefore any data extracted from the database are almost immediately out of date.\" any?in 5Gb data? ","format":"1","timestamp":"1275668407","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0x\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2199"},{"cid":"2200","pid":"0","nid":"9556","subject":"Ways of exploring the data (without downloading it) ","comment":"The guardian have produced a COINS Explorer interface for people who want to browse the data here: http:\/\/coins.guardian.co.uk\/coins-explorer\/search\r\n\r\nThe guardian site allows you to drill down into particular departments or areas of the dataset and then to export a CSV file. By heading deep enough into the data it should be possible to get simple CSV files which will open even in old versions of Excel etc. \r\n\r\nThe WhereDoesMyMoneyGo website also host a copy of the dataset here: http:\/\/coins.wheredoesmymoneygo.org\/coins\r\n\r\nFor anyone who just wants to browse what\'s available at present - those should save a lot of hacking about with the data. ","format":"1","timestamp":"1275667325","name":"TimDavies","mail":"tim@practicalparticipation.co.uk","homepage":"","uid":"3455","registered_name":"TimDavies","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-3de038bf40070161272fcfa75743b4fd\";s:9:\"conf_mail\";s:32:\"tim@practicalparticipation.co.uk\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1273005885-1005040d2fc5151a01\";s:7:\"captcha\";s:5:\"MLNGY\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"0y\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2200"},{"cid":"2201","pid":"0","nid":"9556","subject":"Nice!","comment":"I think this might take a few minutes to sift through.\r\n\r\nI would urge everybody to \'read the readme\' (as it were) to be sure you know what it is that you are looking at. At least skim it, especially the \"what the data won\'t tell you\" bit.\r\n\r\nFor people who are just curious as to what it is, pages 11-20 of the guidance pdf have explanations of the column headings which might answer a lot of questions without having to download all the data.\r\n\r\nIt might be helpful for someone to add to the above datasets a \'representative sample\' file with e.g. a hundred or so lines of data, so people can at least get an idea of what it looks like.\r\nRather more detailed\/complicated than \"DWP paid x for a red stapler on April 1st\"...\r\n\r\n-- DW.","format":"1","timestamp":"1275669267","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"0z\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2201"},{"cid":"2202","pid":"0","nid":"9556","subject":"For Linux users","comment":"To decompress the fact table, install p7zip and run \"7za e fact_table_extract_2009_10.zip\".\r\n\r\nThe files themselves are encoded as UTF-16 (not UTF-8) text, which is a remarkably inefficient encoding for data that is probably mostly ASCII to begin with, but that\'s probably the fault of whatever database export\/dump utility they are using on the system.\r\n\r\nWith data of this level of volume, you can\'t expect to use ordinary desktop tools for analysis. The Government should be commended for making this available - I don\'t know of any other democracy reaching this level of transparency.","format":"1","timestamp":"1275669936","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"110\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2202"},{"cid":"2203","pid":"0","nid":"9556","subject":"Impressive","comment":"This is a fantastic initiative.  This sort of transparency should be the \"default\" for all government data.  Now could you guys export this to North America now? ;-)","format":"1","timestamp":"1275671811","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"111\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2203"},{"cid":"2204","pid":"0","nid":"9556","subject":"Data (So Far)","comment":"So I\'ve spent a few hours working at the data - first part was going through the process of putting it in UTF8, then re-writing it into a more traditional CSV, importing the whole thing into MySQL and started rationalizing it for things such as Department Codes, Account ID etc, setting table indexes and pulling out DISTINCT sets.\r\n\r\nUnfortunately the more processing I do the more stags I hit... SQL info result statements included in the CSV, clusters of non-integer account codes and so forth.\r\n\r\nIt looks like the Guardian has beat me to the punch in creating a searchable index, but the data format hasn\'t exactly helped - I understand this was rushed but IMO spitting out cleaned-up data with separate CSVs for each department and a list of department codes in an additional CSV would have taken little additional time on the governments end and have helped those of us not on the civil service payroll enormously :)\r\n\r\n-- Mark","format":"1","timestamp":"1275676316","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"112\/","status":"0","children":[{"cid":"3379","pid":"2204","nid":"9556","subject":"Department CSVs","comment":"\u003cp\u003eCleaned up data in CSVs by department and a list of department codes would be so cool! I can carry out basic analysis but don\'t have the knowhow to clean and organise the data.\u003c\/p\u003e\u003cp\u003eIf you manage it, please post a link ;-)\u003c\/p\u003e","format":"1","timestamp":"1290218595","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"112.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/3379"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2204"},{"cid":"2207","pid":"0","nid":"9556","subject":"Awesome","comment":"This is great. As mentioned above, that this is the raw data is very good. For those who are having a tough time importing it, rest assured that there are a whole bunch of concerned citizens and organisations that will be putting it together in a more digestible format very soon.","format":"1","timestamp":"1275675833","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"114\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2207"},{"cid":"2210","pid":"0","nid":"9556","subject":"Live Data","comment":"It would be nice to see access to the live data, via a database connection.\r\nAnd its all very well expecting people to create software to access the data, but it would be great if some code that reads the files was made available along with it, that would go along way to explaining the format of the data.","format":"1","timestamp":"1275679045","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"115\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2210"},{"cid":"2212","pid":"0","nid":"9556","subject":"So many people complaining about the format...","comment":"It\'s possibly the best format this data could have been released in. Seriously, this way anyone with a bit of python\/perl\/php\/ruby\/etc hacking knowledge and first year statistics tuition can do their own data mining and present it to the world, rather than everyone being stuck with the govt\'s pre-chewed spun-to-death version.\r\n\r\nComplaints? Frankly I\'m amazed the government has done this. Long may it continue.","format":"1","timestamp":"1275683522","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"116\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2212"},{"cid":"2218","pid":"0","nid":"9556","subject":"Hard work extracting","comment":"Perhaps in the coming days the data.gov.uk guardians can provide alternative formats for the data.\r\n\r\nHaving spent a full minute downloading the data (wow for torrents), it has taken me a long time to unzip.\r\n\r\nPerhaps encode as ASCII and offer in a .tar.gz format?","format":"1","timestamp":"1275688704","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"118\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2218"},{"cid":"2238","pid":"0","nid":"9556","subject":"Well done","comment":"It is nice to see that the goverment is being open with the information it hold.\r\n\r\nWell done.","format":"1","timestamp":"1275911855","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11a\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2238"},{"cid":"2240","pid":"0","nid":"9556","subject":"Equivalent data set for income?","comment":"Will it be possible to get an equivalent of the COINS dataset for Income that the treasury receives?","format":"1","timestamp":"1275913414","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11b\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2240"},{"cid":"2243","pid":"0","nid":"9556","subject":"A few more useful links","comment":"The Open Knowledge Foundation have been logging some of their learning on accessing the data in this Etherpad: http:\/\/pad.okfn.org\/coins \r\n\r\nThe page includes links to spreadsheets created to work out what the codes in the dataset mean, contains some example python code for accessing the data. It also links to this set of Python scripts: http:\/\/bitbucket.org\/okfn\/coins\r\n\r\nRosslyn Analytics have imported the data into their analysis tool which generates graphical representation of some of the data: http:\/\/www.rosslynanalytics.com\/newspress\/index.php\/rosslyn-analytics-makes-sense-of-hm-treasury-data\/ \r\n\r\n","format":"1","timestamp":"1275915395","name":"TimDavies","mail":"tim@practicalparticipation.co.uk","homepage":"","uid":"3455","registered_name":"TimDavies","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-3de038bf40070161272fcfa75743b4fd\";s:9:\"conf_mail\";s:32:\"tim@practicalparticipation.co.uk\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1273005885-1005040d2fc5151a01\";s:7:\"captcha\";s:5:\"MLNGY\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"11c\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2243"},{"cid":"2244","pid":"0","nid":"9556","subject":"Improved spend visibility ","comment":"Rosslyn Analytics, a London-based technology company that specializes in enabling organisations to quickly and easily obtain spend visibility, has launched a dedicated portal that gives the general public the ability to view the UK government\u2019s recently published public sector data from COINS.  This portal can be found at https:\/\/rapidgateway.rapidintel.com. ","format":"1","timestamp":"1275923637","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11d\/","status":"0","children":[{"cid":"3685","pid":"2244","nid":"9556","subject":"Rapid Gateway access - login ","comment":"\u003cp\u003eThe userid and password given on the site, do not work.\u003c\/p\u003e\u003cp\u003ePeter.\u003c\/p\u003e\u003cp\u003e\u0026nbsp;\u003c\/p\u003e","format":"6","timestamp":"1296004832","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11d.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/3685"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2244"},{"cid":"2247","pid":"0","nid":"9556","subject":"Tips for Linux users","comment":"The compressed file can be extracted using 7zip. The result is a text file in UTF-16 encoding which can be converted to the more common UTF-8 encoding using iconv. The NONE strings can be removed using sed.\r\n\r\nExtract the data:\r\n\r\n7z e filename.zip\r\n\r\nwhere \"filename.zip\" is, for example, fact_table_extract_2009_10.zip.\r\n\r\nConvert from UTF-16 to UTF-8:\r\n\r\niconv -f utf-16 -t utf-8 filename.txt \u003e filename.utf-8.txt\r\n\r\nRemove NONE strings:\r\n\r\ncat filename.utf-8.txt | sed -e \'s\/@NONE\/@\/g\' \u003e filename.utf-8.noNone.txt\r\n\r\nOr, more succinctly, you can do the whole job in one go:\r\n\r\n7z -so e filename.zip | iconv -f utf-16 -t utf-8 | sed -e \'s\/@NONE\/@\/g\' \u003e filename.utf-8.noNone.txt\r\n\r\nOn Debian based systems, 7z is part of the p7zip-full package.\r\n\r\nHope that helps someone.\r\n","format":"1","timestamp":"1275934974","name":"paulzarucki","mail":"paulzarucki@googlemail.com","homepage":"","uid":"3665","registered_name":"paulzarucki","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-451b1b00c3c57ff35b3ffabe73795273\";s:9:\"conf_mail\";s:26:\"paulzarucki@googlemail.com\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1275933888-10060769b95abe3005\";s:7:\"captcha\";s:5:\"jMXTG\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"11e\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2247"},{"cid":"2252","pid":"0","nid":"9556","subject":"Linux users more tips","comment":"#!\/bin\/bash\r\nwget -o getdatai.coinsUrls2010.log -i coinsUrls2010\r\nwget -o getdata.coinsUrls2009.log -i coinsUrls2009\r\n\r\nfor i in `ls -1 *.zip`\r\ndo\r\n echo uncompressing and cleaning $i\r\n cat $i | funzip | tr -dc \"[:alnum:][:space:][:punct:]\" \u003e ..\/data\/$i.txt\r\n rm $i\r\ndone\r\n\r\n\r\n\r\nnote that using a stream decompressor such as funzip means you dont need p7 or large files support\r\n Ive put the out turn data into a html format a bit like the gurdian on \r\n http:\/\/www.publicspendingdata.co.uk\/\r\n\r\nand there are also .csv files of just the Outturn data for you to download and analyze in excel...  the files are pretty small and easily downloadable which might be useful for those suffering decompression difficulties... ","format":"1","timestamp":"1275988405","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11f\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2252"},{"cid":"2254","pid":"0","nid":"9556","subject":"Tips for Linux users - correction","comment":"The method I gave in my last comment for converting from UTF-16 to UTF-8 doesn\'t work for the large files due to a limitation in iconv.\r\n\r\nInstead, you can use a small Perl script. Copy the following four lines into a text editor:\r\n\r\n#!\/usr\/bin\/perl\r\nbinmode(STDOUT, \':raw:encoding(UTF-8)\');\r\nbinmode(STDIN, \':raw:encoding(UTF-16)\');\r\nprint while \u003cSTDIN\u003e;\r\n\r\nSave the file as \"utf16to8.pl\" in your home directory. Make the file executable:\r\n\r\nchmod +x utf16to8.pl\r\n\r\nNow you can convert a text file of any size from UTF-16 to UTF-8 as follows:\r\n\r\n~\/utf16to8.pl \u003c filename.txt \u003e filename.utf-8.txt\r\n\r\nOr, to unzip, convert and remove NONEs all in one go, type:\r\n\r\n7z -so e filename.zip | ~\/utf16to8.pl | sed -e \'s\/@NONE\/@\/g\' \u003e filename.utf-8.noNone.txt","format":"1","timestamp":"1276008653","name":"paulzarucki","mail":"paulzarucki@googlemail.com","homepage":"","uid":"3665","registered_name":"paulzarucki","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-451b1b00c3c57ff35b3ffabe73795273\";s:9:\"conf_mail\";s:26:\"paulzarucki@googlemail.com\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1275933888-10060769b95abe3005\";s:7:\"captcha\";s:5:\"jMXTG\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"11g\/","status":"0","children":[{"cid":"2265","pid":"2254","nid":"9556","subject":"Re: Tips for Linux users","comment":"This was very helpful - thank you. The iconv solution worked fine on my 64bit Ubuntu 10.04 system.","format":"1","timestamp":"1276072771","name":"ian.dickinson","mail":"i.j.dickinson@gmail.com","homepage":"","uid":"897","registered_name":"ian.dickinson","signature":"","signature_format":"0","picture":"","data":"a:4:{s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";s:13:\"form_build_id\";s:37:\"form-8d6f4cf38b07105f51f5996f149844c3\";}","thread":"11g.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2265"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2254"},{"cid":"2255","pid":"0","nid":"9556","subject":"Tips for Linux users - correction 2","comment":"Sorry, the HTML filtering on the web site corrupted the text file in my previous comment. Here it is again:\r\n\r\n#!\/usr\/bin\/perl\r\nbinmode(STDOUT, \':raw:encoding(UTF-8)\');\r\nbinmode(STDIN, \':raw:encoding(UTF-16)\');\r\nprint while \u0026lt;STDIN\u0026gt;;\r\n","format":"1","timestamp":"1276007590","name":"paulzarucki","mail":"paulzarucki@googlemail.com","homepage":"","uid":"3665","registered_name":"paulzarucki","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-451b1b00c3c57ff35b3ffabe73795273\";s:9:\"conf_mail\";s:26:\"paulzarucki@googlemail.com\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1275933888-10060769b95abe3005\";s:7:\"captcha\";s:5:\"jMXTG\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"11h\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2255"},{"cid":"2258","pid":"0","nid":"9556","subject":"Patience required","comment":"To all those who are complaining about the size of the files, format, etc, please just have a bit of patience. There are many groups who are working to provide more person-friendly ways of drilling down into this data. It\'s a \u003cem\u003emassive\u003c\/em\u003e step that it has been released at all - I\'ve been involved in open data for some time, and I didn\'t expect HMT to release COINS data on anything like this timescale. So kudos to them. Everyone else just hang-on a short while until the user-friendly interfaces come along, or better still pitch in with ideas of the capabilities you want. What queries would you want to ask if you had a suitably user-friendly tool?","format":"1","timestamp":"1276072345","name":"ian.dickinson","mail":"i.j.dickinson@gmail.com","homepage":"","uid":"897","registered_name":"ian.dickinson","signature":"","signature_format":"0","picture":"","data":"a:4:{s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";s:13:\"form_build_id\";s:37:\"form-8d6f4cf38b07105f51f5996f149844c3\";}","thread":"11i\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2258"},{"cid":"2264","pid":"0","nid":"9556","subject":"Problems with the adjustments file","comment":"Is anyone else having problems with the adjustments file? Having converted the 2009-10 file to utf8, I\'m finding that some records have newlines in them, so that when I try to import the file into PostgresQL the loader complains that lines are truncated. I\'m also seeing some lines that have more fields than they should.","format":"1","timestamp":"1276074254","name":"ian.dickinson","mail":"i.j.dickinson@gmail.com","homepage":"","uid":"897","registered_name":"ian.dickinson","signature":"","signature_format":"0","picture":"","data":"a:4:{s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";s:13:\"form_build_id\";s:37:\"form-8d6f4cf38b07105f51f5996f149844c3\";}","thread":"11j\/","status":"0","children":[{"cid":"2298","pid":"2264","nid":"9556","subject":"Adjustment Files - Rosslyn","comment":"The adjustment files were very poorly prepared. We found thousands of errors in both files. We had to adjust our data validation tool and create a version just for these files. Combinations of missing end of lines and poor column delimeters - who ever thought of using \'@\' to seperate columns, when this is also widely used in the descriptions. Obviously the data prepartion must have been done in a hurry and not tested.\r\nCouple of hints - start looking for the following in the rows and replace the \'@\' with a space:\r\n1.   \' @ \'\r\n2.   \'@ xx-\' where xx can be any value from 01 to 31\r\nTools such as UltraEdit are quite useful but you really need to a data validation application that can be modified on the fly, else these files will not be accurate.\r\nPlease visit https:\/\/rapidgateway.rapidintel.com to get access to the data in user friendly format.","format":"1","timestamp":"1276337865","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11j.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/2298"},{"cid":"2450","pid":"2264","nid":"9556","subject":"2009_10 adjustments file","comment":"Hi Ian\r\nI\'ve not got any embedded newlines. however, there are a lot of files with embedded @ signs in the data, leading to (I think) 466 lines with broken formatting. Notwithstanding comments on the site, it\'s not simple to identify where these have gone wrong with general regex\'s: 528 lines have the string \"@ \", 8295 the string \" @\", 406 lines have the string \" @ \".\r\n\r\nI think that the only realistic way to get this fixed is to ask for better exporting mechanism.\r\n\r\nI find it ironic that there\'s a big ad for the semantic web on this page as SW depends on accurate data.\r\n\r\nI must say that I\'m struggling to understand what the data means, eg there seem to be some very odd records (GDP figures and GDP deflators), reading the notes, I cannot see how the number of records can fall between forecasts, but it does and some of the snapshots look very short.\r\nTim","format":"1","timestamp":"1278280646","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11j.01\/","status":"0","reply_url":"\/comment\/reply\/9556\/2450"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2264"},{"cid":"2271","pid":"0","nid":"9556","subject":"Geographic Granularity -  a None field","comment":"Local government... (also citizen bodies?) would I am sure appreciate some drill down route-map into what the local spends are... perhaps down to NUTS 3 level or even district council.\r\nFrom a quick scan of the code table there I can\'t see a way into this.. ","format":"1","timestamp":"1276083177","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11k\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2271"},{"cid":"2282","pid":"0","nid":"9556","subject":"More tips for Linux users","comment":"The file adjustment_table_extract_2009_10.txt contains many broken lines, i.e. some fields contain one or more newline characters. Here is a small Perl script to convert from UTF-16 to UTF-8, repair the breaks and do some filtering:\r\n\r\n#!\/usr\/bin\/perl\r\n#  - convert text encoding from UTF-16 to UTF-8\r\n#  - convert DOS\/Windows newlines (CR-LF) to host system\'s newlines\r\n#  - fix broken lines (spurious line breaks in some records)\r\n#  - delete \"NONE\"s\r\n#\r\n# Examples of usage:\r\n#\tcoins.pl 82 \u003c infile.txt \u003e outfile.txt\r\n#\tzcat infile.gz | coins.pl 82 \u003e outfile.txt\r\n#\t7z -so e infile.zip | coins.pl 82 \u003e outfile.txt\r\n#\r\nmy $fields = $ARGV[0];  # Number of fields expected (81 in fact table, 82 in adjustment table)\r\nmy $part;\r\nbinmode(STDIN, \':raw:encoding(UTF-16)\');\r\nbinmode(STDOUT, \':raw:encoding(UTF-8)\');\r\nwhile (\u0026lt;STDIN\u0026gt;) {\r\n\ts\/[\\n\\r]\/\/g;  # remove CR and LF\r\n\ts\/\\@NONE\/@\/g;  # remove \"NONE\"\r\n\tmy $data = $_;\r\n\tmy $str = $data;  # count the number of fields\r\n\t$str =~ s\/[^@]\/\/g;\r\n\tif (length($str) \u003e $fields-2) {  # enough fields?\r\n\t\tprint \"$data\\n\";\r\n\t\t$part = \"\";\r\n\t} else {  # not enough fields\r\n\t\t$part .= $data;  # join the parts that we have so far\r\n\t\t$str = $part;\r\n\t\t$str =~ s\/[^@]\/\/g;\r\n\t\tif (length($str) \u003e $fields-2) {  # do we have enough now?\r\n\t\t\tprint \"$part\\n\";\r\n\t\t\t$part = \"\";\r\n\t\t}\r\n\t}\r\n}\r\n","format":"1","timestamp":"1276163499","name":"paulzarucki","mail":"paulzarucki@googlemail.com","homepage":"","uid":"3665","registered_name":"paulzarucki","signature":"","signature_format":"0","picture":"","data":"a:6:{s:13:\"form_build_id\";s:37:\"form-451b1b00c3c57ff35b3ffabe73795273\";s:9:\"conf_mail\";s:26:\"paulzarucki@googlemail.com\";s:6:\"mollom\";a:2:{s:10:\"session_id\";s:29:\"1275933888-10060769b95abe3005\";s:7:\"captcha\";s:5:\"jMXTG\";}s:7:\"contact\";i:1;s:14:\"picture_delete\";s:0:\"\";s:14:\"picture_upload\";s:0:\"\";}","thread":"11m\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2282"},{"cid":"2285","pid":"0","nid":"9556","subject":"The coins data is actually","comment":"The coins data is actually pretty small\r\n\r\ntry www.publicspendingdata.co.uk for smal csv files for each department \/ Program \/ account ","format":"1","timestamp":"1276166104","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11n\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2285"},{"cid":"2437","pid":"0","nid":"9556","subject":"data quality questions","comment":"I wonder why these data are encoded in utf16?\r\n\r\nIs there a formal description of the schema - the data\'s hardly exported in tnf, but it would at least be nice to get the format descriptions. I cannot find this info in the treasury docs.\r\n\r\nfwiw, the raw data for facts..2009_10 compresses down to 15MB with bzip2 after ripping out the NONEs, as opposed to the 70MB on the web site.","format":"1","timestamp":"1278082835","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11o\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/2437"},{"cid":"3119","pid":"0","nid":"9556","subject":"Raw data, hard to digest","comment":"\u003cp\u003eHi there, I agree with the chaps that you have done a wonderful job releasing all this information. And I also agree that though the format may not be ideal, the various technologies for its dissemination are a good choice. However, I\'d make a tentative suggestion... Now that you have the data readily at hand, you might as well make it a little bit more digestible.\u003c\/p\u003e\u003cp\u003eTo bring you an example, my company produces mobile VAS solutions for big telcos, and we get immense amount of raw data. My line managers expect me to provide them with intelligible insights that enable them to make informed decisions. So I dig through the pile, slice it and dice it, until it makes sense. I do not draw conclusions, at least not explicitly, nor make decision, only possible suggestions of alternative ways for interpretation.\u003c\/p\u003e\u003cp\u003eI think in this case, the public does expect two things. The raw data, so the government can be held accountable. And an informative, easy to undertsand form of what the essence of 44 gigs of this data is. (Yes, I know, I am fully aware that it gives rise to criticism, but let\'s face it, what does not?)\u003c\/p\u003e\u003cp\u003eThanks,\u003c\/p\u003e\u003cp\u003eLefty\u003c\/p\u003e\u003cp\u003e\u0026nbsp;\u003c\/p\u003e\u003cp\u003e\u0026nbsp;\u003c\/p\u003e","format":"1","timestamp":"1286207400","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11p\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/3119"},{"cid":"3315","pid":"0","nid":"9556","subject":"Very user-unfriendly","comment":"\u003cp\u003eThis data is clearly not designed for Joe Public to use.\u003c\/p\u003e\u003cp\u003eCreating lists of huge files\u0026nbsp;without meaningful description is the worst way to manage and present information.\u003c\/p\u003e\u003cp\u003eTransparency is great, but only if people can find the information they want.\u003c\/p\u003e\u003cp\u003e2\/10 for this effort.\u003c\/p\u003e","format":"1","timestamp":"1290159358","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11q\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/3315"},{"cid":"3334","pid":"0","nid":"9556","subject":"Seruritie Vunribilities","comment":"\u003cp\u003e\u003cspan style=\"font-size: 12pt; color: black;\"\u003e\u003cspan style=\"font-family: Arial;\"\u003eUsing Bit Torrent, which is know to transmit viruses, re-enforces my feeling Government don\'t want people to understand and scrutinise this information.\u003c\/span\u003e\u003c\/span\u003e\u003c\/p\u003e","format":"1","timestamp":"1290173095","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11r\/","status":"0","children":[{"cid":"3854","pid":"3334","nid":"9556","subject":"Bit Torrent does not transmit","comment":"\u003cp\u003eBit Torrent does not transmit viruses. People who wish to infect your computer with a virus, publish copied versions of a computer program with a virus installed on public Bit-Torrent websites.\u003cbr \/\u003e\u003cbr \/\u003e\u003c\/p\u003e\u003cp\u003eThis site is not for the public to add torrents, they have only been created the site owners. The files are CSV files which cannot be used to transmit viruses.\u003cbr \/\u003e\u003cbr \/\u003e\u003c\/p\u003e\u003cp\u003e\u003cstrong\u003eViruses are only spread via Bit Torrent when the author of the Torrent intended you to download a virus.\u003c\/strong\u003e\u003c\/p\u003e","format":"6","timestamp":"1297920731","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11r.00\/","status":"0","reply_url":"\/comment\/reply\/9556\/3854"}],"ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/3334"},{"cid":"3382","pid":"0","nid":"9556","subject":"Raw data - we must trust someone to digest it","comment":"\u003cp\u003eThere are various comments here about the impossibility of digesting all this data.\u0026nbsp; I welcome the move to transparency but note all the requests for a summary in an \"easy to use form\".\u0026nbsp; Although the raw data is useful for those with the time and skills to be \"armchair auditors\" it would be wrong for this to become the only form of audit.\u0026nbsp; Surely the \"easy to use form\" is a set of published financial statements, together with assurance from an independent, trusted source that those statements represent a true and fair view?\u003c\/p\u003e\u003cp\u003eDoesn\'t everything we see on this site emphasise the value of the National Audit Office and related functions\u0026nbsp;for Scotland, Wales, the health service and local government?\u003c\/p\u003e\u003cp\u003eCraig A\u003c\/p\u003e","format":"1","timestamp":"1290241465","name":"","mail":"","homepage":"","uid":"0","registered_name":"","signature":"","signature_format":"0","picture":"","data":None,"thread":"11s\/","status":"0","ckan_package_id":"3266d22c-9d0f-4ebe-b0bc-ea622f858e15","reply_url":"\/comment\/reply\/9556\/3382"}]
example_comments_html = '''
  <div id="comments">
                	<a href="/comment/reply/9556#comment-form" title="Share your thoughts and opinions related to this posting." id="comment-add" class="custom">Add new comment</a>
            <h2 id="comments-title">Comments (89)</h2>
        <a id="comment-3382"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3382" class="active">Raw data - we must trust someone to digest it</a></h3>

  <div class="submitted">
    Sat, 20/11/2010 - 08:24 �� Anonymous  </div>

  <div class="content">
    <p>There are various comments here about the impossibility of digesting all this data.&nbsp; I welcome the move to transparency but note all the requests for a summary in an "easy to use form".&nbsp; Although the raw data is useful for those with the time and skills to be "armchair auditors" it would be wrong for this to become the only form of audit.&nbsp; Surely the "easy to use form" is a set of published financial statements, together with assurance from an independent, trusted source that those statements represent a true and fair view?</p>
<p>Doesn\'t everything we see on this site emphasise the value of the National Audit Office and related functions&nbsp;for Scotland, Wales, the health service and local government?</p>
<p>Craig A</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3382">reply</a></li>
</ul></div>
<a id="comment-3334"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3334" class="active">Seruritie Vunribilities</a></h3>

  <div class="submitted">
    Fri, 19/11/2010 - 13:24 — Anonymous  </div>

  <div class="content">
    <p>Using Bit Torrent, which is know to transmit viruses, re-enforces my feeling Government don\'t want people to understand and scrutinise this information.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3334">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-3854"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3854" class="active">Bit Torrent does not transmit</a></h3>

  <div class="submitted">
    Thu, 17/02/2011 - 05:32 — Anonymous  </div>

  <div class="content">
    <p>Bit Torrent does not transmit viruses. People who wish to infect your computer with a virus, publish copied versions of a computer program with a virus installed on public Bit-Torrent websites.</p>
<p>This site is not for the public to add torrents, they have only been created the site owners. The files are CSV files which cannot be used to transmit viruses.</p>
<p><strong>Viruses are only spread via Bit Torrent when the author of the Torrent intended you to download a virus.</strong></p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3854">reply</a></li>
</ul></div>
</div><a id="comment-3315"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3315" class="active">Very user-unfriendly</a></h3>

  <div class="submitted">
    Fri, 19/11/2010 - 09:35 — Anonymous  </div>

  <div class="content">
    <p>This data is clearly not designed for Joe Public to use.</p>
<p>Creating lists of huge files&nbsp;without meaningful description is the worst way to manage and present information.</p>
<p>Transparency is great, but only if people can find the information they want.</p>
<p>2/10 for this effort.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3315">reply</a></li>
</ul></div>
<a id="comment-3119"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3119" class="active">Raw data, hard to digest</a></h3>

  <div class="submitted">
    Mon, 04/10/2010 - 15:50 — Anonymous  </div>

  <div class="content">
    <p>Hi there, I agree with the chaps that you have done a wonderful job releasing all this information. And I also agree that though the format may not be ideal, the various technologies for its dissemination are a good choice. However, I\'d make a tentative suggestion... Now that you have the data readily at hand, you might as well make it a little bit more digestible.</p>
<p>To bring you an example, my company produces mobile VAS solutions for big telcos, and we get immense amount of raw data. My line managers expect me to provide them with intelligible insights that enable them to make informed decisions. So I dig through the pile, slice it and dice it, until it makes sense. I do not draw conclusions, at least not explicitly, nor make decision, only possible suggestions of alternative ways for interpretation.</p>
<p>I think in this case, the public does expect two things. The raw data, so the government can be held accountable. And an informative, easy to undertsand form of what the essence of 44 gigs of this data is. (Yes, I know, I am fully aware that it gives rise to criticism, but let\'s face it, what does not?)</p>
<p>Thanks,</p>
<p>Lefty</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3119">reply</a></li>
</ul></div>
<a id="comment-2437"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2437" class="active">data quality questions</a></h3>

  <div class="submitted">
    Fri, 02/07/2010 - 15:00 — Anonymous  </div>

  <div class="content">
    <p>I wonder why these data are encoded in utf16?</p>
<p>Is there a formal description of the schema - the data\'s hardly exported in tnf, but it would at least be nice to get the format descriptions. I cannot find this info in the treasury docs.</p>
<p>fwiw, the raw data for facts..2009_10 compresses down to 15MB with bzip2 after ripping out the NULLs, as opposed to the 70MB on the web site.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2437">reply</a></li>
</ul></div>
<a id="comment-2285"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2285" class="active">The coins data is actually</a></h3>

  <div class="submitted">
    Thu, 10/06/2010 - 10:35 — Anonymous  </div>

  <div class="content">
    <p>The coins data is actually pretty small</p>
<p>try <a href="http://www.publicspendingdata.co.uk" title="www.publicspendingdata.co.uk">www.publicspendingdata.co.uk</a> for smal csv files for each department / Program / account</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2285">reply</a></li>
</ul></div>
<a id="comment-2282"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2282" class="active">More tips for Linux users</a></h3>

  <div class="submitted">
    Thu, 10/06/2010 - 09:51 — <a href="/users/paulzarucki" title="View user profile.">paulzarucki</a>  </div>

  <div class="content">
    <p>The file adjustment_table_extract_2009_10.txt contains many broken lines, i.e. some fields contain one or more newline characters. Here is a small Perl script to convert from UTF-16 to UTF-8, repair the breaks and do some filtering:</p>
<p>#!/usr/bin/perl<br />
#  - convert text encoding from UTF-16 to UTF-8<br />
#  - convert DOS/Windows newlines (CR-LF) to host system\'s newlines<br />
#  - fix broken lines (spurious line breaks in some records)<br />
#  - delete "NULL"s<br />
#<br />
# Examples of usage:<br />
#	coins.pl 82 &lt; infile.txt &gt; outfile.txt<br />
#	zcat infile.gz | coins.pl 82 &gt; outfile.txt<br />
#	7z -so e infile.zip | coins.pl 82 &gt; outfile.txt<br />
#<br />
my $fields = $ARGV[0];  # Number of fields expected (81 in fact table, 82 in adjustment table)<br />
my $part;<br />
binmode(STDIN, \':raw:encoding(UTF-16)\');<br />
binmode(STDOUT, \':raw:encoding(UTF-8)\');<br />
while (&lt;STDIN&gt;) {<br />
	s/[\n\r]//g;  # remove CR and LF<br />
	s/\@NULL/@/g;  # remove "NULL"<br />
	my $data = $_;<br />
	my $str = $data;  # count the number of fields<br />
	$str =~ s/[^@]//g;<br />
	if (length($str) &gt; $fields-2) {  # enough fields?<br />
		print "$data\n";<br />
		$part = "";<br />
	} else {  # not enough fields<br />
		$part .= $data;  # join the parts that we have so far<br />
		$str = $part;<br />
		$str =~ s/[^@]//g;<br />
		if (length($str) &gt; $fields-2) {  # do we have enough now?<br />
			print "$part\n";<br />
			$part = "";<br />
		}<br />
	}<br />
}</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2282">reply</a></li>
</ul></div>
<a id="comment-2271"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2271" class="active">Geographic Granularity -  a null field</a></h3>

  <div class="submitted">
    Wed, 09/06/2010 - 11:32 — Anonymous  </div>

  <div class="content">
    <p>Local government... (also citizen bodies?) would I am sure appreciate some drill down route-map into what the local spends are... perhaps down to NUTS 3 level or even district council.<br />
From a quick scan of the code table there I can\'t see a way into this..</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2271">reply</a></li>
</ul></div>
<a id="comment-2264"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2264" class="active">Problems with the adjustments file</a></h3>

  <div class="submitted">
    Wed, 09/06/2010 - 09:04 — <a href="/users/iandickinson" title="View user profile.">ian.dickinson</a>  </div>

  <div class="content">
    <p>Is anyone else having problems with the adjustments file? Having converted the 2009-10 file to utf8, I\'m finding that some records have newlines in them, so that when I try to import the file into PostgresQL the loader complains that lines are truncated. I\'m also seeing some lines that have more fields than they should.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2264">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-2450"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2450" class="active">2009_10 adjustments file</a></h3>

  <div class="submitted">
    Sun, 04/07/2010 - 21:57 — Anonymous  </div>

  <div class="content">
    <p>Hi Ian<br />
I\'ve not got any embedded newlines. however, there are a lot of files with embedded @ signs in the data, leading to (I think) 466 lines with broken formatting. Notwithstanding comments on the site, it\'s not simple to identify where these have gone wrong with general regex\'s: 528 lines have the string "@ ", 8295 the string " @", 406 lines have the string " @ ".</p>
<p>I think that the only realistic way to get this fixed is to ask for better exporting mechanism.</p>
<p>I find it ironic that there\'s a big ad for the semantic web on this page as SW depends on accurate data.</p>
<p>I must say that I\'m struggling to understand what the data means, eg there seem to be some very odd records (GDP figures and GDP deflators), reading the notes, I cannot see how the number of records can fall between forecasts, but it does and some of the snapshots look very short.<br />
Tim</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2450">reply</a></li>
</ul></div>
<a id="comment-2298"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2298" class="active">Adjustment Files - Rosslyn</a></h3>

  <div class="submitted">
    Sat, 12/06/2010 - 10:17 — Anonymous  </div>

  <div class="content">
    <p>The adjustment files were very poorly prepared. We found thousands of errors in both files. We had to adjust our data validation tool and create a version just for these files. Combinations of missing end of lines and poor column delimeters - who ever thought of using \'@\' to seperate columns, when this is also widely used in the descriptions. Obviously the data prepartion must have been done in a hurry and not tested.<br />
Couple of hints - start looking for the following in the rows and replace the \'@\' with a space:<br />
1.   \' @ \'<br />
2.   \'@ xx-\' where xx can be any value from 01 to 31<br />
Tools such as UltraEdit are quite useful but you really need to a data validation application that can be modified on the fly, else these files will not be accurate.<br />
Please visit <a href="https://rapidgateway.rapidintel.com" title="https://rapidgateway.rapidintel.com">https://rapidgateway.rapidintel.com</a> to get access to the data in user friendly format.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2298">reply</a></li>
</ul></div>
</div><a id="comment-2258"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2258" class="active">Patience required</a></h3>

  <div class="submitted">
    Wed, 09/06/2010 - 08:32 — <a href="/users/iandickinson" title="View user profile.">ian.dickinson</a>  </div>

  <div class="content">
    <p>To all those who are complaining about the size of the files, format, etc, please just have a bit of patience. There are many groups who are working to provide more person-friendly ways of drilling down into this data. It\'s a <em>massive</em> step that it has been released at all - I\'ve been involved in open data for some time, and I didn\'t expect HMT to release COINS data on anything like this timescale. So kudos to them. Everyone else just hang-on a short while until the user-friendly interfaces come along, or better still pitch in with ideas of the capabilities you want. What queries would you want to ask if you had a suitably user-friendly tool?</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2258">reply</a></li>
</ul></div>
<a id="comment-2255"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2255" class="active">Tips for Linux users - correction 2</a></h3>

  <div class="submitted">
    Tue, 08/06/2010 - 14:33 — <a href="/users/paulzarucki" title="View user profile.">paulzarucki</a>  </div>

  <div class="content">
    <p>Sorry, the HTML filtering on the web site corrupted the text file in my previous comment. Here it is again:</p>
<p>#!/usr/bin/perl<br />
binmode(STDOUT, \':raw:encoding(UTF-8)\');<br />
binmode(STDIN, \':raw:encoding(UTF-16)\');<br />
print while &lt;STDIN&gt;;</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2255">reply</a></li>
</ul></div>
<a id="comment-2254"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2254" class="active">Tips for Linux users - correction</a></h3>

  <div class="submitted">
    Tue, 08/06/2010 - 14:50 — <a href="/users/paulzarucki" title="View user profile.">paulzarucki</a>  </div>

  <div class="content">
    <p>The method I gave in my last comment for converting from UTF-16 to UTF-8 doesn\'t work for the large files due to a limitation in iconv.</p>
<p>Instead, you can use a small Perl script. Copy the following four lines into a text editor:</p>
<p>#!/usr/bin/perl<br />
binmode(STDOUT, \':raw:encoding(UTF-8)\');<br />
binmode(STDIN, \':raw:encoding(UTF-16)\');<br />
print while ;</p>
<p>Save the file as "utf16to8.pl" in your home directory. Make the file executable:</p>
<p>chmod +x utf16to8.pl</p>
<p>Now you can convert a text file of any size from UTF-16 to UTF-8 as follows:</p>
<p>~/utf16to8.pl &lt; filename.txt &gt; filename.utf-8.txt</p>
<p>Or, to unzip, convert and remove NULLs all in one go, type:</p>
<p>7z -so e filename.zip | ~/utf16to8.pl | sed -e \'s/@NULL/@/g\' &gt; filename.utf-8.nonull.txt</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2254">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-2265"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2265" class="active">Re: Tips for Linux users</a></h3>

  <div class="submitted">
    Wed, 09/06/2010 - 08:39 — <a href="/users/iandickinson" title="View user profile.">ian.dickinson</a>  </div>

  <div class="content">
    <p>This was very helpful - thank you. The iconv solution worked fine on my 64bit Ubuntu 10.04 system.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2265">reply</a></li>
</ul></div>
</div><a id="comment-2252"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2252" class="active">Linux users more tips</a></h3>

  <div class="submitted">
    Tue, 08/06/2010 - 09:13 — Anonymous  </div>

  <div class="content">
    <p>#!/bin/bash<br />
wget -o getdatai.coinsUrls2010.log -i coinsUrls2010<br />
wget -o getdata.coinsUrls2009.log -i coinsUrls2009</p>
<p>for i in `ls -1 *.zip`<br />
do<br />
 echo uncompressing and cleaning $i<br />
 cat $i | funzip | tr -dc "[:alnum:][:space:][:punct:]" &gt; ../data/$i.txt<br />
 rm $i<br />
done</p>
<p>note that using a stream decompressor such as funzip means you dont need p7 or large files support<br />
 Ive put the out turn data into a html format a bit like the gurdian on<br />
 <a href="http://www.publicspendingdata.co.uk/" title="http://www.publicspendingdata.co.uk/">http://www.publicspendingdata.co.uk/</a></p>
<p>and there are also .csv files of just the Outturn data for you to download and analyze in excel...  the files are pretty small and easily downloadable which might be useful for those suffering decompression difficulties...</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2252">reply</a></li>
</ul></div>
<a id="comment-2247"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2247" class="active">Tips for Linux users</a></h3>

  <div class="submitted">
    Mon, 07/06/2010 - 18:22 — <a href="/users/paulzarucki" title="View user profile.">paulzarucki</a>  </div>

  <div class="content">
    <p>The compressed file can be extracted using 7zip. The result is a text file in UTF-16 encoding which can be converted to the more common UTF-8 encoding using iconv. The NULL strings can be removed using sed.</p>
<p>Extract the data:</p>
<p>7z e filename.zip</p>
<p>where "filename.zip" is, for example, fact_table_extract_2009_10.zip.</p>
<p>Convert from UTF-16 to UTF-8:</p>
<p>iconv -f utf-16 -t utf-8 filename.txt &gt; filename.utf-8.txt</p>
<p>Remove NULL strings:</p>
<p>cat filename.utf-8.txt | sed -e \'s/@NULL/@/g\' &gt; filename.utf-8.nonull.txt</p>
<p>Or, more succinctly, you can do the whole job in one go:</p>
<p>7z -so e filename.zip | iconv -f utf-16 -t utf-8 | sed -e \'s/@NULL/@/g\' &gt; filename.utf-8.nonull.txt</p>
<p>On Debian based systems, 7z is part of the p7zip-full package.</p>
<p>Hope that helps someone.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2247">reply</a></li>
</ul></div>
<a id="comment-2244"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2244" class="active">Improved spend visibility </a></h3>

  <div class="submitted">
    Mon, 07/06/2010 - 15:13 — Anonymous  </div>

  <div class="content">
    <p>Rosslyn Analytics, a London-based technology company that specializes in enabling organisations to quickly and easily obtain spend visibility, has launched a dedicated portal that gives the general public the ability to view the UK government’s recently published public sector data from COINS.  This portal can be found at <a href="https://rapidgateway.rapidintel.com" title="https://rapidgateway.rapidintel.com">https://rapidgateway.rapidintel.com</a>.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2244">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-3685"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3685" class="active">Rapid Gateway access - login </a></h3>

  <div class="submitted">
    Wed, 26/01/2011 - 01:20 — Anonymous  </div>

  <div class="content">
    <p>The userid and password given on the site, do not work.</p>
<p>Peter.</p>
<p>&nbsp;</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3685">reply</a></li>
</ul></div>
</div><a id="comment-2243"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2243" class="active">A few more useful links</a></h3>

  <div class="submitted">
    Mon, 07/06/2010 - 12:56 — <a href="/users/timdavies" title="View user profile.">TimDavies</a>  </div>

  <div class="content">
    <p>The Open Knowledge Foundation have been logging some of their learning on accessing the data in this Etherpad: <a href="http://pad.okfn.org/coins" title="http://pad.okfn.org/coins">http://pad.okfn.org/coins</a> </p>
<p>The page includes links to spreadsheets created to work out what the codes in the dataset mean, contains some example python code for accessing the data. It also links to this set of Python scripts: <a href="http://bitbucket.org/okfn/coins" title="http://bitbucket.org/okfn/coins">http://bitbucket.org/okfn/coins</a></p>
<p>Rosslyn Analytics have imported the data into their analysis tool which generates graphical representation of some of the data: <a href="http://www.rosslynanalytics.com/newspress/index.php/rosslyn-analytics-makes-sense-of-hm-treasury-data/" title="http://www.rosslynanalytics.com/newspress/index.php/rosslyn-analytics-makes-sense-of-hm-treasury-data/">http://www.rosslynanalytics.com/newspress/index.php/rosslyn-analytics-ma...</a></p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2243">reply</a></li>
</ul></div>
<a id="comment-2240"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2240" class="active">Equivalent data set for income?</a></h3>

  <div class="submitted">
    Mon, 07/06/2010 - 12:23 — Anonymous  </div>

  <div class="content">
    <p>Will it be possible to get an equivalent of the COINS dataset for Income that the treasury receives?</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2240">reply</a></li>
</ul></div>
<a id="comment-2238"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2238" class="active">Well done</a></h3>

  <div class="submitted">
    Mon, 07/06/2010 - 11:57 — Anonymous  </div>

  <div class="content">
    <p>It is nice to see that the goverment is being open with the information it hold.</p>
<p>Well done.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2238">reply</a></li>
</ul></div>
<a id="comment-2218"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2218" class="active">Hard work extracting</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 21:58 — Anonymous  </div>

  <div class="content">
    <p>Perhaps in the coming days the data.gov.uk guardians can provide alternative formats for the data.</p>
<p>Having spent a full minute downloading the data (wow for torrents), it has taken me a long time to unzip.</p>
<p>Perhaps encode as ASCII and offer in a .tar.gz format?</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2218">reply</a></li>
</ul></div>
<a id="comment-2212"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2212" class="active">So many people complaining about the format...</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 20:32 — Anonymous  </div>

  <div class="content">
    <p>It\'s possibly the best format this data could have been released in. Seriously, this way anyone with a bit of python/perl/php/ruby/etc hacking knowledge and first year statistics tuition can do their own data mining and present it to the world, rather than everyone being stuck with the govt\'s pre-chewed spun-to-death version.</p>
<p>Complaints? Frankly I\'m amazed the government has done this. Long may it continue.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2212">reply</a></li>
</ul></div>
<a id="comment-2210"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2210" class="active">Live Data</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 19:17 — Anonymous  </div>

  <div class="content">
    <p>It would be nice to see access to the live data, via a database connection.<br />
And its all very well expecting people to create software to access the data, but it would be great if some code that reads the files was made available along with it, that would go along way to explaining the format of the data.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2210">reply</a></li>
</ul></div>
<a id="comment-2207"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2207" class="active">Awesome</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 18:23 — Anonymous  </div>

  <div class="content">
    <p>This is great. As mentioned above, that this is the raw data is very good. For those who are having a tough time importing it, rest assured that there are a whole bunch of concerned citizens and organisations that will be putting it together in a more digestible format very soon.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2207">reply</a></li>
</ul></div>
<a id="comment-2204"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2204" class="active">Data (So Far)</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 18:31 — Anonymous  </div>

  <div class="content">
    <p>So I\'ve spent a few hours working at the data - first part was going through the process of putting it in UTF8, then re-writing it into a more traditional CSV, importing the whole thing into MySQL and started rationalizing it for things such as Department Codes, Account ID etc, setting table indexes and pulling out DISTINCT sets.</p>
<p>Unfortunately the more processing I do the more stags I hit... SQL info result statements included in the CSV, clusters of non-integer account codes and so forth.</p>
<p>It looks like the Guardian has beat me to the punch in creating a searchable index, but the data format hasn\'t exactly helped - I understand this was rushed but IMO spitting out cleaned-up data with separate CSVs for each department and a list of department codes in an additional CSV would have taken little additional time on the governments end and have helped those of us not on the civil service payroll enormously :)</p>
<p>-- Mark</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2204">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-3379"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-3379" class="active">Department CSVs</a></h3>

  <div class="submitted">
    Sat, 20/11/2010 - 02:03 — Anonymous  </div>

  <div class="content">
    <p>Cleaned up data in CSVs by department and a list of department codes would be so cool! I can carry out basic analysis but don\'t have the knowhow to clean and organise the data.</p>
<p>If you manage it, please post a link ;-)</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/3379">reply</a></li>
</ul></div>
</div><a id="comment-2203"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2203" class="active">Impressive</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 17:16 — Anonymous  </div>

  <div class="content">
    <p>This is a fantastic initiative.  This sort of transparency should be the "default" for all government data.  Now could you guys export this to North America now? ;-)</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2203">reply</a></li>
</ul></div>
<a id="comment-2202"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2202" class="active">For Linux users</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 16:45 — Anonymous  </div>

  <div class="content">
    <p>To decompress the fact table, install p7zip and run "7za e fact_table_extract_2009_10.zip".</p>
<p>The files themselves are encoded as UTF-16 (not UTF-8) text, which is a remarkably inefficient encoding for data that is probably mostly ASCII to begin with, but that\'s probably the fault of whatever database export/dump utility they are using on the system.</p>
<p>With data of this level of volume, you can\'t expect to use ordinary desktop tools for analysis. The Government should be commended for making this available - I don\'t know of any other democracy reaching this level of transparency.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2202">reply</a></li>
</ul></div>
<a id="comment-2201"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2201" class="active">Nice!</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 16:34 — Anonymous  </div>

  <div class="content">
    <p>I think this might take a few minutes to sift through.</p>
<p>I would urge everybody to \'read the readme\' (as it were) to be sure you know what it is that you are looking at. At least skim it, especially the "what the data won\'t tell you" bit.</p>
<p>For people who are just curious as to what it is, pages 11-20 of the guidance pdf have explanations of the column headings which might answer a lot of questions without having to download all the data.</p>
<p>It might be helpful for someone to add to the above datasets a \'representative sample\' file with e.g. a hundred or so lines of data, so people can at least get an idea of what it looks like.<br />
Rather more detailed/complicated than "DWP paid x for a red stapler on April 1st"...</p>
<p>-- DW.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2201">reply</a></li>
</ul></div>
<a id="comment-2200"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2200" class="active">Ways of exploring the data (without downloading it) </a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 16:02 — <a href="/users/timdavies" title="View user profile.">TimDavies</a>  </div>

  <div class="content">
    <p>The guardian have produced a COINS Explorer interface for people who want to browse the data here: <a href="http://coins.guardian.co.uk/coins-explorer/search" title="http://coins.guardian.co.uk/coins-explorer/search">http://coins.guardian.co.uk/coins-explorer/search</a></p>
<p>The guardian site allows you to drill down into particular departments or areas of the dataset and then to export a CSV file. By heading deep enough into the data it should be possible to get simple CSV files which will open even in old versions of Excel etc. </p>
<p>The WhereDoesMyMoneyGo website also host a copy of the dataset here: <a href="http://coins.wheredoesmymoneygo.org/coins" title="http://coins.wheredoesmymoneygo.org/coins">http://coins.wheredoesmymoneygo.org/coins</a></p>
<p>For anyone who just wants to browse what\'s available at present - those should save a lot of hacking about with the data.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2200">reply</a></li>
</ul></div>
<a id="comment-2199"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2199" class="active">another concern</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 16:20 — Anonymous  </div>

  <div class="content">
    <p>I do not want to complain on the weight or the format of the data, but it seems to me that this is just a query from a database and nobody did care about the quality after it (who uses @ as a separation element?!?!. the most difficult thing is not importing the data in this or that system but controlling that everything is correct because a few records do not import in the right shape. however, I really enjoy reading this sentence from the guidance booklet "Therefore any data extracted from the database are almost immediately out of date." any?in 5Gb data?</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2199">reply</a></li>
</ul></div>
<a id="comment-2194"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2194" class="active">The Plan</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 15:00 — Anonymous  </div>

  <div class="content">
    <p>To those complaining about the format and size of the data....</p>
<p>The new government has stated that they expect the digesting, analysis and redistribution of this data to be conducted by 3rd parties. These 3rd parties, who are willing to put money into making the data more readable and then potentially sell it on, are the ones who are more likely to download and use the data in it\'s current form.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2194">reply</a></li>
</ul></div>
<a id="comment-2190"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2190" class="active">Good Choice</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 14:30 — Anonymous  </div>

  <div class="content">
    <p>I\'m glad to see this data available, and shared in such a format that allows for easy analysis.</p>
<p>The choice of sharing medium (bittorrent) is also a good choice. It allows large files to be shared while reduce load on the host server, and therefore lowering the necessary server costs saving tax payer money. In theory at least.</p>
<p>Thank you.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2190">reply</a></li>
</ul></div>
<a id="comment-2188"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2188" class="active">Corrupt zip file ?</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:55 — Anonymous  </div>

  <div class="content">
    <p>Zipped 2009/10 Fact table, 67MiB (4.28GiB uncompressed) is coming up as corrupt when I try and extract the contents.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2188">reply</a></li>
</ul></div>
<a id="comment-2187"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2187" class="active">addressing some concerns</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:50 — Anonymous  </div>

  <div class="content">
    <p>to all the people who are commenting that the information is being released in a difficult to consume form, this is GOOD. this is what we really need, the RAW data. if it were sliced up into easier to consume packages, or presented in nice webpages, it would just mean the civil service taking us further away from the raw original data in the form it was produced, further from the truth basically.</p>
<p>now that the raw data has been released, hacker types (in the traditional sense) the world over can dig through it and present it in any form they/you want. in the coming weeks months and years you will start to see other websites where you will be able to browse, consume and interpret the data in every form imaginable, from traditional spreadsheet style interfaces to insane hollywood style 3d topographical visualisations. these will be built by citizens, using the raw data finally releaed here by government. this page and these csv files are meant for consumption by these hackers, if they were put into a form easily understandable/consumable by the general public this would completely defeat the point of the exercise.</p>
<p>right, off to hack some code! ive been looking for a data set to feed into those python machine learning algorithms they taught us at uni...</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2187">reply</a></li>
</ul></div>
<a id="comment-2182"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2182" class="active">Formatting</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:29 — Anonymous  </div>

  <div class="content">
    <p>Could whomever is responsible for creating these files please give it another go with the following:</p>
<p>1. Use UTF-8 or ASCII instead of UTF-8 - Almost half this file is empty space!<br />
2. Use proper CSV, double quoted where needed<br />
3. Compress to RAR<br />
4. Replace NULL with an empty field.</p>
<p>I\'ve just done it here on my side and been able to reduce the 09-10 file down from the original 4 GB to 1.8GB, 23MB RAR - which is small enough to open in Excel if you\'ve got 6+ GB of RAM installed.</p>
<p>- Mark Randall</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2182">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-2222"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2222" class="active">Re: Formatting</a></h3>

  <div class="submitted">
    Sat, 05/06/2010 - 11:39 — Anonymous  </div>

  <div class="content">
    <p>3. Compress to RAR</p>
<p>Right, you want open and transparent data that\'s compressed using a proprietary algorithm. Isn\'t that defeating the purpose? Not to mention, PPMd and LZMA (as implemented by 7-zip) have generally yielded higher compression ratios than RAR\'s proprietary mess.</p>
<p>Not to mention that any RAR files created would be wholly illegal unless someone paid for WinRAR. No such restriction on 7-zip and it\'s technologies.</p>
<p>From the WinRAR license:</p>
<p>   8. There are no additional license fees, <strong>apart from the cost of purchasing a license</strong>, associated with the creation and distribution of RAR archives, volumes, self-extracting archives or self-extracting volumes. Legally registered owners may use their copies of RAR/WinRAR to produce archives and self-extracting archives and to distribute those archives free of any additional RAR royalties.</p>
<p>In short, you must pay for a license before you can distribute archives. The whole purpose of opening up this dataset is to allow anyone to audit the government\'s spending, with the goal of reducing wasteful spending. Paying for WinRAR when superior and free alternatives exist is just more wasteful spending.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2222">reply</a></li>
</ul></div>
<a id="comment-2213"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2213" class="active">RAR is inappropriate</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 20:57 — Anonymous  </div>

  <div class="content">
    <p>As it is a secret, proprietary format which cannot be opened with free software.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2213">reply</a></li>
</ul></div>
<a id="comment-2198"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2198" class="active">sorry Mark...</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 16:00 — Anonymous  </div>

  <div class="content">
    <p>...it\'s not the number of bytes that\'s important here but the number of records (rows). We all know that we can reduce the number of fields (columns) as many are redundant and others are irrelevant, but 2+ mln records are too many for Xls, also if you have just two fields. I can open the entire 4Gb in Xls but before visualize the content I\'m told not the entire file would be open...</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2198">reply</a></li>
</ul></div>
</div><a id="comment-2178"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2178" class="active">Making the Data Accessible</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:23 — Anonymous  </div>

  <div class="content">
    <p>Please provide this data in a form that can be drilled down from within a browser. </p>
<p>You get a tick for making the data available, but loose points for inaccessibility!</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2178">reply</a></li>
</ul></div>
<a id="comment-2175"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2175" class="active">Is this CSV?</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:18 — Anonymous  </div>

  <div class="content">
    <p>I unzipped the (non-torrent) version of the 09/10 adjustment table and it wasn\'t CSV but rather 2-sign delimited (think tab-delim with an @ instead of a tab). also the data wasn\'t clean for import to something like Excel as it had some lines of non-table data at the end - just the sort of thing to upset already hard-pushed spreadsheet importers on non-high end rigs.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2175">reply</a></li>
</ul></div>
<a id="comment-2174"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2174" class="active">Checksum for 2009/10 zip file</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:13 — Anonymous  </div>

  <div class="content">
    <p>sha1sum fact_table_extract_2009_10.zip<br />
c163e7e1fba578e38bb3cf295bd1be0514d2fcf9  fact_table_extract_2009_10.zip</p>
<p>Corrupt on unzipping. Does anyone else get a different sha1sum checksum for this file?</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2174">reply</a></li>
</ul></div>
<a id="comment-2173"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2173" class="active">COINS contains millions of</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:12 — Anonymous  </div>

  <div class="content">
    <p>COINS contains millions of rows of data; as a consequence the files are large and the data held within the files complex.  Using these download files will require some degree of technical competence and expertise in handling and manipulating large volumes of data.  It is likely that these data will be most easily used by organisations that have the relevant expertise, rather than by individuals. By having access to these data, institutions and experts will be able to process and present them in a way that is more accessible to the general public. In addition, subsets of data from the COINS database will also be made available in more accessible formats by August 2010.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2173">reply</a></li>
</ul></div>
<a id="comment-2170"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2170" class="active">Mac problems?</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 13:04 — <a href="/users/pezholio" title="View user profile.">pezholio</a><span class="author-pane-moderator"> | <img src="/sites/all/modules/advanced_forum/styles/naked/images/icon_moderator.png">Moderator</span>  </div>

  <div class="content">
    <p>It seems the out of the box unarchiver on OSX can\'t deal with large files, such as the COINS fact table. It spits out a cpgz file, which if you try to unzip just creates another zip, and so on, and so on.</p>
<p>Thankfully I managed to unzip it using Keka (<a href="http://www.kekaosx.com/en/" title="http://www.kekaosx.com/en/">http://www.kekaosx.com/en/</a>), which is an OSX form of 7zip. This worked without any problems. Just thought I\'d share in case anyone else was having any difficulties.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2170">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-7695"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-7695" class="active">keka</a></h3>

  <div class="submitted">
    Tue, 13/12/2011 - 23:17 — Anonymous (not verified)  </div>

  <div class="content">
    <p>Thanks for this. &nbsp;I hadn\'t tried it yet but have no doubt I would have had the same problems.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/7695">reply</a></li>
</ul></div>
</div><a id="comment-2168"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2168" class="active">Unable to open</a></h3>

  <div class="submitted">
    Fri, 04/06/2010 - 12:53 — Anonymous  </div>

  <div class="content">
    <p>Typical Tory duplicity - how the hell is an ordinary person meant to open this.</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2168">reply</a></li>
</ul></div>
<div class="indented"><a id="comment-2221"></a>
<div class="comment comment-published clear-block">
  
  
  <h3><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15#comment-2221" class="active">Try the user interface</a></h3>

  <div class="submitted">
    Sat, 05/06/2010 - 11:02 — Anonymous  </div>

  <div class="content">
    <p>Try the user interface provided by the guardian newspaper</p>
<p>geoff</p>
      </div>

  <ul class="links"><li class="comment_reply first last"><a href="/comment/reply/9556/2221">reply</a></li>
</ul></div>
</div><div class="item-list"><ul class="pager"><li class="pager-current first">1</li>
<li class="pager-item"><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15?page=1" title="Go to page 2" class="active">2</a></li>
<li class="pager-next"><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15?page=1" title="Go to next page" class="active">next ��</a></li>
<li class="pager-last last"><a href="/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15?page=1" title="Go to last page" class="active">last</a></li>
</ul></div>  </div>
'''
