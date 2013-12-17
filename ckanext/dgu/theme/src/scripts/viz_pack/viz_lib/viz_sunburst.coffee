window.viz ?= {}

class viz.Sunburst
    constructor: (@selector,root) ->
        width = 500
        height = 500
        radius = Math.min(width, height) / 2
        color = d3.scale.category10()
        caption = d3.select(@selector)
          .select('.caption')

        svg = d3.select(@selector)
          .append("svg")
          .attr("width", width)
          .attr("height", height)
          .append("g")
          .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
        @partition = d3.layout.partition()
          .sort(null)
          .size([2 * Math.PI, radius * radius])
          .value((d) -> Math.log(d.size))
        @arc = d3.svg.arc()
          .startAngle((d) -> d.x)
          .endAngle((d) -> d.x + d.dx)
          .innerRadius((d) -> Math.sqrt d.y)
          .outerRadius((d) -> Math.sqrt d.y + d.dy)
        path = svg.datum(root)
          .selectAll("path")
          .data(@partition.nodes)
          .enter()
          .append("path")
          .attr("display", (d) -> (if d.depth then null else "none"))
          .attr("d", @arc)
          .style("stroke", "#fff")
          .style("fill", (d) -> 
            if d.children
              '#ccc'
            else if d.name=='(others)' 
              '#eee'
            else 
              color d.name
          )
          .style("fill-rule", "evenodd")
          .on('mouseover', (d)-> 
            caption.html '<p>£'+viz.money_to_string(d.size)+'</p><small>'+d.name+'</small>'
          )
          .on('mouseout', (d)-> caption.html '')

    logarithmic: =>
        console.log 'logarithmic'
        @partition.value((d) -> Math.log(d.size))

    linear: =>
        console.log 'linear'
        @partition.value((d) -> d.size)
        console.log @partition.nodes
        svg = d3.select(@selector)
        svg.selectAll('path')
          .data(@partition.nodes)



