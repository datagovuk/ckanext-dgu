#!/bin/bash

IMAGES=../theme/src/images

./snapshot_object.js "http://localhost:3008/data/viz/social-investment-and-foundations" \
  social_investment_totals $IMAGES/graph-socialinvestment1.png\
  social_investment_sankey $IMAGES/graph-socialinvestment2.png\
  social_investment_coinvestment $IMAGES/graph-socialinvestment3.png

./snapshot_object.js "http://localhost:3008/data/viz/investment-readiness-programme"\
  sib_container $IMAGES/graph-investmentreadiness1.png\
  icrf_container $IMAGES/graph-investmentreadiness2.png
