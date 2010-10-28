{
	"name": "CKAN DGU API",
	"base_url": "http://catalogue.data.gov.uk",
	"pages": {
		"/": {
			"status": 200, 
			"contains": ["Welcome to the data.gov.uk catalogue"]
		}
	},
	"calls": {
		"/api/2/rest/package": {
                        "contains": "abortion"
                },
		"/api/2/rest/package/abstract_of_scottish_agricultural_statistics": {
                        "contains": "Scottish Government"
                },
		"/api/2/rest/tag": {
                        "contains": "weather"
                },
		"/api/2/rest/group": {
                        "contains": "68e4746a-7a79-4cf7-9525-b29e64b096c6"
                },
		"/api/2/rest/revision": {
                        "contains": "cf9cb335-6ac0-41b6-930d-a8c84228147a"
                },
		"/api/2/rest/revision/cf9cb335-6ac0-41b6-930d-a8c84228147a": {
                        "contains": "2010-02-09"
                },
		"/api/2/form/package/create": {
			"status": 403
                },
		"/api/2/form/package/edit/staff-organograms-and-pay-ofwat": {
			"status": 403
		},
		"/api/2/rest/package": {
                        "method": "POST",
                        "data": "invalid",
			"status": 403
		},
		"/api/2/rest/package/staff-organograms-and-pay-ofwat": {
                        "method": "POST",
                        "data": "invalid",
			"status": 403
		}
	}
}