
window.viz ?= {}

viz.renderPieChart = (data, containerSelector, colorFunction, trimLegend=-1, legendData=null) ->
    legendData ?= data.map (x) -> x.name
    width = 450
    height = 200
    radius = Math.min(width, height) / 2
    arc = d3.svg.arc()\
      .outerRadius(radius - 10)\
      .innerRadius(radius - 50)
    pie = d3.layout.pie()\
      .sort(null)\
      .value((d) -> d.value)
    container = $(containerSelector)
    caption = $('<div class="caption"/>').appendTo(container)

    svg = d3.select(containerSelector)\
      .append("svg")\
      .attr("width", width)\
      .attr("height", height)\
      .append("g")\
      .attr("transform", "translate("+(15+radius)+"," + height / 2 + ")")

    g = svg.selectAll(".arc")\
      .data(pie(data))\
      .enter()\
      .append("g")\
      .attr("class", "arc")
    g.append("path")\
      .attr("d", arc)\
      .style("fill", (d) -> colorFunction(d.data.name))\
      .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d.data.name))\
      .attr("data-col1", (d) -> colorFunction(d.data.name))\
      .attr("data-col2", (d) -> d3.rgb(colorFunction(d.data.name)).brighter .5)\
      .attr('data-caption',(d)->'£'+viz.money_to_string d.value)

    legendData = data.map (d)->d.name
    viz.legend( d3.select(containerSelector), legendData, colorFunction, trimLegend )

    # Dynamic captioning
    container.find('path').bind 'hoverend', (e) ->
      caption.html ''
    container.find('path').bind 'hoverstart', (e) ->
      caption.html this.getAttribute('data-caption')
