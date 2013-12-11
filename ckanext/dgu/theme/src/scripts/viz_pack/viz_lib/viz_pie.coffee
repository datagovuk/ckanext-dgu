window.viz ?= {}

class viz.PieChart
    constructor: (@selector, data, @colorFunction, trimLegend=-1, legendData=null) ->
        legendData ?= data.map (x) -> x.name
        width = 450
        height = 200
        radius = Math.min(width, height) / 2
        @arc = d3.svg.arc()
          .outerRadius(radius - 10)
          .innerRadius(radius - 50)
        @pie = d3.layout.pie()
          .sort(null)\
          .value((d) -> d.value)
        container = $(@selector)

        @svg = d3.select(@selector)
          .append("svg")
          .attr("width", width)
          .attr("height", height)
          .append("g")
          .attr("transform", "translate("+(15+radius)+"," + height / 2 + ")")

        @path = @svg.datum(data).selectAll('path')
          .data(@pie)
          .enter().append('path')
          .attr('fill',(d,i)=> @colorFunction d.data.name)
          .attr('d',@arc)
          .each((d)-> @._current = d)
          .attr('data-caption',(d)->'£'+viz.money_to_string d.value)
          .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d.data.name))

        #   .attr("data-col1", (d) => @colorFunction(d.data.name))
        #   .attr("data-col2", (d) => d3.rgb(@colorFunction(d.data.name)).brighter .5)

        legendData = data.map (d)->d.name
        viz.legend( d3.select(@selector), legendData, @colorFunction, trimLegend )

        # Dynamic captioning
        caption = d3.select(@selector).select('.caption')
        container.find('path').bind 'hoverend', (e) ->
          caption.html ''
        container.find('path').bind 'hoverstart', (e) ->
          caption.html @getAttribute('data-caption')

    setData: (data) ->
        $('.hoverable').trigger('hoverend')
        captureArc = @arc
        arcTween = (a) ->
          i = d3.interpolate(@._current, a)
          @._current = i(0)
          return (t) -> captureArc(i(t))
        @path = @svg.datum(data).selectAll('path')
          .data(@pie)
          .attr('data-caption',(d)->'£'+viz.money_to_string d.value)
          .transition().duration(800).delay(100)
          .attrTween("d", arcTween)
