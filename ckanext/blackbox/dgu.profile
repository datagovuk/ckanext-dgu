{
	"name": "DGU CKAN",
	"base_url": "http://hmg.ckan.net",
	"pages": {
		"/": {
			"status": 200, 
			"contains": ["Top Tags", "Recently changed", "Welcome to"]
		},
		"/package": {
			"contains": ["Register a new package", "Browse packages"],
			"status": 200,
			"form": {
				"0": {
					"q": "abandoned",
					"@submit": {
						"status": 200,
						"contains": "Search Data Packages",
						"not contains": "0 packages found"
					}
				}
			}
		},
		"/package/list": {
				"contains": "abandoned"
	  },
		"/package/new": {
			"status": 200, 
			"contains": "Register a New Data Package",
			"click": {
				"Browse": {
					"contains": "Package listing"
				} 
			}
		},
		"/package/staff-organograms-and-pay-ofwat": {
			"status": 200, 
			"contains": ["staff-organograms-and-pay-ofwat", "Organogram and staff pay data for Ofwat"],
			"click": {
				"Subscribe": {
					"status": 200
				}
			}
		},
		"/package/history/staff-organograms-and-pay-ofwat": {
			"contains": ["Revision", "Timestamp", "Author"]
		},
		"/package/edit/staff-organograms-and-pay-ofwat": {
			"status": 200,
			"contains": ["Edit Data Package: staff-organograms-and-pay-ofwat", "Preview"],
			"button": {
				"Preview": {
					"contains": "Preview"
				}
			}
		},
		"/group": {
			"status": 200,
			"contains": ["ukgov", "Uk Government"],
			"click": {
				"Uk Government": {
					"contains": "hmg"
				}
			}
		},
		"/tag": {
			"status": 200, 
			"contains": "accessibility",
			"click": {
				"accessibility": {
					"contains": "Tag: accessibility"
				}
			}
		}
	}
}