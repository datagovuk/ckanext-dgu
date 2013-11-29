window.viz ?= {}

# Draw the coinvestment thing
viz.renderGroupedBar = ->
  margin =
    top: 20
    right: 20
    bottom: 30
    left: 40

  width  = 960 - margin.left - margin.right
  height = 500 - margin.top - margin.bottom
  x0     = d3.scale.ordinal().rangeRoundBands([0, width], .1)
  x1     = d3.scale.ordinal()
  y      = d3.scale.linear().range([height, 0])
  color  = d3.scale.ordinal().range(["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"])
  xAxis  = d3.svg.axis().scale(x0).orient("bottom")
  yAxis  = d3.svg.axis().scale(y).orient("left").tickFormat(d3.format(".2s"))
  svg    = d3.select("#graph_coinvestment")\
    .append("svg")\
    .attr("width", width + margin.left + margin.right)\
    .attr("height", height + margin.top + margin.bottom)\
    .append("g")\
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
  d3.json "data/etl_coinvestment.json", (data) ->
    x0.domain data.series.map((d) -> d.major)
    x1.domain(data.legend).rangeRoundBands [0, x0.rangeBand()]
    y.domain [0, d3.max(data.series, (d) -> d3.max d.ages, (d) -> d.value )]

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
      .text("Population")
    state = svg.selectAll(".state")\
      .data(data.series)\
      .enter()\
      .append("g")\
      .attr("class", "g")\
      .attr("transform", (d) -> "translate(" + x0(d.major) + ",0)")
    state.selectAll("rect")\
      .data((d) -> d.ages)\
      .enter()\
      .append("rect")\
      .attr("width", x1.rangeBand())\
      .attr("x", (d) -> x1(d.name))\
      .attr("y", (d) -> y(d.value))\
      .attr("height", (d) -> height - y(d.value))\
      .style("fill", (d) -> color d.name )
    legend = svg.selectAll(".legend")\
      .data(data.legend.slice().reverse())\
      .enter()\
      .append("g")\
      .attr("class", "legend")\
      .attr("transform", (d, i) -> "translate(0," + i * 20 + ")")
    legend.append("rect")\
      .attr("x", width - 18)\
      .attr("width", 18)\
      .attr("height", 18)\
      .style("fill", color)
    legend.append("text")\
      .attr("x", width - 24)\
      .attr("y", 9)\
      .attr("dy", ".35em")\
      .style("text-anchor", "end")\
      .text((d) -> d)
