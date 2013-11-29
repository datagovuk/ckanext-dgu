window.viz ?= {}

# Draw the coinvestment bubble chart
viz.renderBubbleChart = (data,graphSelector,colorFunction) ->
  margin =
    top: 20
    right: 20
    bottom: 30
    left: 40
  width  = 760 - margin.left - margin.right
  height = 300 - margin.top - margin.bottom
  x      = d3.time.scale().range([0,width])
  y      = d3.scale.linear().range([height, 0])
  xAxis  = d3.svg.axis().scale(x).orient("bottom")
  yAxis  = d3.svg.axis().scale(y).orient("left").tickFormat(d3.format(".2s"))
  svg    = d3.select(graphSelector)\
    .append("svg")\
    .attr("width", width + margin.left + margin.right)\
    .attr("height", height + margin.top + margin.bottom)\
    .append("g")\
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
  min_date = d3.min data.points, (d)->d.date
  max_date = d3.max data.points, (d)->d.date
  x.domain [min_date,max_date]
  y.domain [0, d3.max(data.points, (d) -> d.y )]
  svg.append("g")\
    .attr("class", "x axis")\
    .attr("transform", "translate(0," + height + ")")\
    .call(xAxis)
  svg.append("g")\
    .attr("class", "y axis")\
    .call(yAxis)\
    .append("text")\
    .attr("transform", "rotate(-90)")\
    .attr("y", 6)\
    .attr("dy", ".71em")\
    .style("text-anchor", "end")\
    .text("(£)   Coinvestment")
  circle = svg.selectAll(".circle")\
    .data(data.points)\
    .enter()\
    .append("circle")\
    .attr("r", (d) -> d.radius)\
    .attr("transform", (d)->
      _x = x(d.date)
      _y = y(d.y)
      return 'translate('+_x+','+_y+')'
    )\
    .attr('class',(d)->'hoverable hover-'+viz.text_to_css_class(d.origin))\
    .style("fill", (d)->colorFunction(d.origin) )
    .attr("data-col1", (d)->colorFunction(d.origin) )
    .attr("data-col2", (d)->d3.rgb(colorFunction(d.origin)).brighter .5 )

  viz.legend( d3.select(graphSelector), data.legend, colorFunction )

