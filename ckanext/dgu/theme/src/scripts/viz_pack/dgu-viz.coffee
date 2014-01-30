window.viz ?= {}

# Social Investments & Foundations
# --------------------------------
window.viz.loadFrontPage = ->
    barChart = new viz.frontPageStackedBar( window.viz_graph_datasets )


class window.viz.frontPageStackedBar
    constructor: (data) ->
        @setData data

    setData: (data) ->
        data = d3.csv.parse(data)
        stack = ['published','unpublished']

        #console.log 'graphing',data
        margin = 
            top: 20
            right: 20
            bottom: 20
            left: 40
        width = 560 - margin.left - margin.right
        height = 300 - margin.top - margin.bottom
        # Graph settings
        # --------------
        x = d3.scale.ordinal()
            .rangeRoundBands([0, width], .1)
        y = d3.scale.linear()
            .rangeRound([height, 0])
        color = d3.scale.ordinal()
            .range(["#8BC658", "#bedba4"])
        xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
        yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .tickFormat(d3.format(".2s"))
        svg = d3.select(".graph1").append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .style("margin", "0 auto")
          .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
        color.domain(  d3.keys(data[0]).filter((key)->key!="date")  )
        data.forEach((d)->
            y0 = 0
            d.ages = color.domain().map((name)->{name: name, y0: y0, y1: y0 += +d[name]})
            d.total = d.ages[d.ages.length - 1].y1
        )
        x.domain( data.map((d)->d.date) )
        y.domain( [0, d3.max(data, (d)->d.total)] )
        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .append("text")
            .attr("x", 6)
            .attr("y", 6)
            .attr("dy", ".71em")
            .text("Weekly Sample")
        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)
            .append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text("No. of Datasets")
        state = svg.selectAll(".state")
            .data(data)
            .enter().append("g")
                .attr("class", "g")
                .attr("transform", (d) -> "translate("+x(d.date)+",0)" )
        state.selectAll("rect")
              .data((d) -> d.ages )
          .enter().append("rect")
              .attr("width", x.rangeBand())
              .attr("y", (d) -> y(d.y1) )
              .attr("height", (d) -> y(d.y0) - y(d.y1) )
              .style("fill", (d) -> color(d.name) )
        legend = svg.selectAll(".legend")
            .data(color.domain().slice().reverse())
          .enter().append("g")
            .attr("class", "legend")
            .attr("transform", (d,i) -> "translate(0,"+i*20+")" );
        legend.append("rect")
            .attr("x", width/3 - 18)
            .attr("width", 18)
            .attr("height", 18)
            .style("fill", color)
        legend.append("text")
            .attr("x", width/3 - 24)
            .attr("y", 9)
            .attr("dy", ".35em")
            .style("text-anchor", "end")
            .text((d)->d )




# Social Investments & Foundations
# --------------------------------
window.viz.loadSocialInvestmentsAndFoundations = ->
  d3.json "/scripts/json/social_investments_and_foundations/graphs.json", (data) ->
    # Initialise sector colors
    data.pie1['all'].forEach (x) -> 
      viz.sector_color x.name
      viz.sector_list.push x.name
    graph_sankey = new viz.Sankey "#graph_sankey",data.sankey
    graph_stackedBar = new viz.StackedBarChart '#graph_yearonyear', data.bar.all
    graph_coinvestmentTotal = new viz.CashTotal '#coinvestment-total', data.coinvestment_total
    graph_investmentTotal = new viz.CashTotal '#investment-total', data.investment_total['all']
    graph_sunburst = new viz.Sunburst '#graph_coinvestment', data.sunburst
    graph_pie1 = new viz.PieChart('#graph_pie1',data.pie1['all'],viz.sector_color,32,viz.sector_list)
    graph_pie2 = new viz.PieChart('#graph_pie2',data.pie2['all'],viz.colour_product_type())
    # Bind to buttons
    $('.foundation-selector a').on 'click', (event) ->
      event.preventDefault()
      key = $(this).attr 'data-key'
      graph_stackedBar.setData data.bar[key]
      graph_pie1.setData data.pie1[key]
      graph_pie2.setData data.pie2[key]
      graph_investmentTotal.setData data.investment_total[key]
      $('.foundation-selector a').removeClass 'active'
      $('.foundation-selector a[data-key="'+key+'"]').addClass 'active'
      return false

    # Bind to all hoverable elements
    $('.hoverable').on 'mouseover', (e) ->
      $('li.hoverable').removeClass 'hovering'
      $('svg .hoverable').each (i,el) ->
          $(el).css
            'fill'   : $(el).attr('data-col1') 
            'stroke' : 'none'
      $('.hoverable').trigger 'hoverend'
      $('circle.hoverable').css('opacity',0.5)
      # get hover class name eg. hover-foo-bar
      classes = $(this).attr('class').split(' ')
      # get hover class name eg. hover-foo-bar
      for x in classes
        if x.substring(0,6)=='hover-'
          elements = $('.'+x)
          elements.trigger 'hoverstart' 
          elements.each (i,el) ->
            el = $(el)
            if el.is('li')
              if e.type=="mouseover"
                el.addClass 'hovering'
              else
                el.removeClass 'hovering'
            else if el.is('rect') or el.is('path') or el.is('circle')
              if e.type=="mouseover"
                el.css('fill',el.attr('data-col2') )
                el.css('stroke','#000' )
              else
                el.css('fill',el.attr('data-col1') )
                el.css('stroke','none' )
              if el.is('circle')
                el.css('opacity',1)

# Social Incubator Fund
# ---------------------
window.viz.loadSocialIncubatorFund = ->
  console.log 'here'


# Util
# ----
viz.trim = (x,maxlen) ->
  if (maxlen>=0) and (x.length>maxlen)
    return x.substr(0,maxlen) + '...'
  return x
viz.money_to_string = (amount) ->
  out = ''
  amount = String(amount)
  while amount.length>3
    out = ',' + amount.substring(amount.length-3) + out
    amount = amount.substring(0,amount.length-3)
  return amount + out
viz.sector_color = d3.scale.category20()
viz.sector_list = []
viz.text_to_css_class = (x) ->
  x.toLowerCase().replace(/[ ]/g,'-').replace(/[^a-z-]/g,'')
viz.colour_product_type = ->
  known_colors = []
  return (x) ->
    index = known_colors.indexOf(x)
    if index==-1
      known_colors.push x
      index = known_colors.indexOf(x)
    if x=='Loans and facilities - Unsecured'
      return d3.rgb('#74C476').brighter 1
    if x=='Loans and facilities - Partially secured'
      return d3.rgb('#74C476')
    return d3.rgb('#193B79').brighter(index/2)


viz.legend = (container,elements,colorFunction,trim=-1) ->
  ul = container
    .append("ul")
    .attr('class','legend')
  ul.selectAll('li')
    .data(elements)
    .enter()
    .append('li')
    .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d))
    .text( (d) -> viz.trim(d,trim) )
    .append('div')
    .attr('class','swatch')
    .style('background-color',colorFunction)

