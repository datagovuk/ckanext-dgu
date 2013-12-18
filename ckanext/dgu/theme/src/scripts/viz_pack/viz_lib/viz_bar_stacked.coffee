window.viz ?= {}

class viz.StackedBarChart 
  constructor: (@selector, data) ->
    margin =
      top: 20
      right: 290
      bottom: 30
      left: 40
    @width  = 920 - margin.left - margin.right
    @height = 500 - margin.top - margin.bottom
    @svg    = d3.select(@selector)
      .append("svg")
      .attr("width", @width + margin.left + margin.right)
      .attr("height", @height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
    # axes match the initial data and do not update
    @x      = d3.scale.ordinal().rangeRoundBands([0, @width], .1)
    @y      = d3.scale.linear().range([@height, 0])
    xAxis  = d3.svg.axis().scale(@x).orient("bottom")
    yAxis  = d3.svg.axis().scale(@y).orient("left").tickFormat(d3.format(".2s"))
    @x.domain data.series.map((d) -> d.major)
    @y.domain [0, d3.max(data.series, (d) -> d3.sum d.elements, (d) -> d.value )]
    # x axis
    @svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + @height + ")")
      .call(xAxis)
    # y axis
    @svg.append("g")
      .attr("class", "y axis")
      .call(yAxis)
      .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text("Cash Invested")
    viz.legend( d3.select('#graph_yearonyear'), viz.sector_list, viz.sector_color, trim=34 )
    # Insert the data
    @setData data

  setData: (data) =>
    # Populate data with offsets
    data.series.forEach (series) ->
      sumOfPrevious = 0
      series.elements.forEach (d) ->
        d.sumOfPrevious = sumOfPrevious
        sumOfPrevious += d.value
      series.sum = sumOfPrevious
    # major series (columns with text)
    column = @svg.selectAll(".column")
      .data(data.series)
    column.enter()
      .append("g")
      .attr("class", "column")
      .append('text')
    column.attr("transform", (d) => "translate(" + @x(d.major) + ",0)")
      .select('text')
      .style('fill','white')
      .text((d)->'£'+viz.money_to_string(d.sum))
      .attr('x',30)
      .attr('y',(d)=>@y(d.sum)-5)
      .transition().duration(500).delay(500)
      .style('fill','black')
    # minor series (rectangles)
    rects = column.selectAll("rect")
      .data((d) -> d.elements)
    rects.enter()
      .append("rect")
      .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d.name))
      .attr("width", @x.rangeBand())
      .attr('y',@height)
      .attr('height',0)
      .style("fill", (d) -> viz.sector_color(d.name))
      .attr('data-col1', (d)->viz.sector_color(d.name))
      .attr('data-col2', (d)->d3.rgb(viz.sector_color(d.name)).brighter 0.3)
    rects.transition().duration(800)
      .attr("y", (d) => @y(d.value+d.sumOfPrevious))
      .attr("height", (d) => @height - @y(d.value))

