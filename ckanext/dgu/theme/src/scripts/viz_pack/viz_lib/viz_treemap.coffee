window.viz ?= {}

class viz.TreeMap
    constructor: (@selector,root) ->
        position = ->
          this.style("left", (d) -> d.x + "px")
            .style("top", (d) -> d.y + "px")
            .style("width", (d) -> Math.max(0, d.dx - 1) + "px")
            .style("height", (d) -> Math.max(0, d.dy - 1) + "px")
        width = 660
        height = 400
        color = d3.scale.category10()
        treemap = d3.layout.treemap()
          .size([width, height])
          .sticky(true).value((d) -> d.size)
        div = d3.select(@selector)
          .append("div")
          .attr('class','rootnode')
          .style("position", "relative")
          .style("width", width + "px")
          .style("height", height + "px")
        node = div.datum(root)
          .selectAll(".node")
          .data(treemap.nodes)
          .enter()
          .append("div")
          .attr("class", "node")
          .call(position)
          .style("background", (d) -> 
            if not d.children
              if d.name=='(others)'
                return '#eee'
              return color d.name
          )
          .text((d) -> (if d.children then null else d.name))
        onChange = ->
          value = (if @value is "count" then ( -> 1 ) else ((d) -> d.size))
          _data = treemap.value(value).nodes
          node.data(_data)
            .transition()
            .duration(1500)
            .call(position)
        d3.selectAll("input").on("change",onChange)

class viz.CirclePack
    constructor: (@selector,root) ->
        diameter = 660
        format = d3.format(",d")
        color = d3.scale.category20c()

        pack = d3.layout.pack()
          .size([diameter - 4, diameter - 4])
          .value((d) -> 
            console.log d
            d.size)

        svg = d3.select(@selector)
          .append("svg")
          .attr("width", diameter)
          .attr("height", diameter)
          .append("g")
          .attr("transform", "translate(2,2)")
        node = svg.datum(root)
          .selectAll(".node")
          .data(pack.nodes)
          .enter()
          .append("g")
          .attr("class", (d) -> (if d.children then "node" else "leaf node"))
          .attr("transform", (d) -> "translate(" + d.x + "," + d.y + ")")
        node.append("title")
          .text((d) -> d.name + ((if d.children then "" else ": " + format(d.size))))

        node.append("circle")
          .attr("r", (d) -> d.r)
          .style('fill',(d)->color d.name)

        node.filter((d) -> not d.children)
          .append("text")
          .attr("dy", ".3em")
          .style("text-anchor", "middle")
          .text((d) -> d.name.substring 0, d.r / 3)



