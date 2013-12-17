window.viz ?= {}

class viz.Sankey 
  
  constructor: (selector,data) ->
    width = 900
    height = 500
    formatNumber = d3.format(",.0f")
    format = (x)-> '£'+viz.money_to_string(x)

    color  = d3.scale.category20c()

    svg  = d3.select(selector)
      .append("svg")
      .attr("width", width)
      .attr("height", height)

    sankey = d3.sankey()
      .nodeWidth(15)
      .nodePadding(10)
      .size([width, height-13])
    path = sankey.link()

    dragmove = (d) ->
      d3.select(this)
        .attr("transform", "translate(" + d.x + "," + (d.y = Math.max(0, Math.min(height - d.dy, d3.event.y))) + ")")
      sankey.relayout()
      link.attr "d", path

    calculateNodeColor = (d) ->
      index = (Math.floor(d.x / 230))
      palette = [
        '#E81308'
        '#FF04A7'
        '#5109FF'
        '#1030FF'
      ]
      # Hacking to achieve a nice effect
      base_color = d3.rgb(palette[index]).brighter 2
      return base_color.darker(d.y/400)

    sankey.nodes(data.nodes)
      .links(data.links)
      .layout(32)
    link = svg.append("g")
      .selectAll(".link")
      .data(data.links)
      .enter()
      .append("path")
      .attr("class", "link")
      .attr("d", path)
      .style("stroke-width", (d) -> Math.max 1, d.dy)
      .sort((a, b) -> b.dy - a.dy)

    link.append("title")
      .text( (d) ->
        out = '';
        for x in d.foundationSplit
          out += '\n'+x[0]+': ' + format(x[1])
        if d.foundationSplit.length>1 
          out += '\n--------------'
          out += '\nTotal: ' + format(d.value)
        return out.substr(1)
      )

    node = svg.append("g")
      .selectAll(".node")
      .data(data.nodes)
      .enter()
      .append("g")
      .attr("class", "node")
      .attr("transform", (d) -> "translate(" + d.x + "," + d.y + ")")
      .call(\
         d3.behavior.drag().origin((d) -> d)\
        .on("dragstart", -> @parentNode.appendChild this)\
        .on("drag", dragmove)\
      )

    node.append("rect")
      .attr("height", (d) -> d.dy)
      .attr("width", sankey.nodeWidth())
      .style("fill", (d) -> d.color = color(d.name.replace(RegExp(" .*"), "")))
      .style("fill", calculateNodeColor)
      .append("title")
      .style("stroke", (d) -> d3.rgb(d.color).darker 2)
      .text((d) -> d.name + "\n" + format(d.value))

    calculateNodeName = (d) ->
      if d.name.length > 40
        return d.name.substr(0,40) + '...'
      d.name

    node.append("text")
      .attr("x", -6)
      .attr("y", (d) -> d.dy / 2)
      .attr("dy", ".35em")
      .attr("text-anchor", "end")
      .attr("transform", null)
      .text(calculateNodeName)
      .filter((d) -> d.x < width / 2)
      .attr("x", 6 + sankey.nodeWidth())
      .attr("text-anchor", "start")
