window.viz ?= {}

class viz.PieChart
    constructor: (@selector, data, @colorFunction, _options={} ) ->
        options = 
            width : 450
            height: 200
            trimLegend: -1
            legendData: data.map (x) -> x.name
            radius: -1
            innerRadius: -1
            legend: true
        for k,v of _options
            options[k] = v
        if options.radius == -1
            options.radius = Math.min(options.width, options.height) / 2
        if options.innerRadius == -1
            options.innerRadius = options.radius - 50
        @arc = d3.svg.arc()
          .outerRadius(options.radius)
          .innerRadius(options.innerRadius)
        @pie = d3.layout.pie()
          .sort(null)\
          .value((d) -> d.value)
        container = $(@selector)

        @svg = d3.select(@selector)
          .append("svg")
          .attr("width", options.width)
          .attr("height", options.height)
          .append("g")
          .attr("transform", "translate("+(options.radius)+"," + options.radius + ")")

        @path = @svg.datum(data).selectAll('path')
          .data(@pie)
          .enter().append('path')
          .attr('fill',(d,i)=> @colorFunction d.data.name)
          .attr('d',@arc)
          .each((d)-> @._current = d)
          .attr('data-caption',(d)->'£'+viz.money_to_string d.value)
          .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d.data.name))

        if options.legend
          viz.legend( d3.select(@selector), options.legendData, @colorFunction, options.trimLegend )

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
