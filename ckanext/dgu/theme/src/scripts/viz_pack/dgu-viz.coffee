window.viz ?= {}

# Document.onload()
# -----------------
$ ->
  d3.json "/json/social_investments_and_foundations/graphs.json", (data) ->
    # Initialise sector colors
    data.pie1.forEach (x) -> 
      viz.sector_color x.name
      viz.sector_list.push x.name
    # Render Sankey of discrete relationships
    viz.renderSankey data.sankey
    # Render bar chart of yearly performance
    viz.renderStackedBar data.bar
    # Render totals
    $('#coinvestment-total').html( '<span class="poundsign">£</span>'+viz.money_to_string data.coinvestment_total )
    $('#investment-total').html( '<span class="poundsign">£</span>'+viz.money_to_string data.investment_total )
    # Render Bubblechart of coinvestments
    data.bubble.points.forEach (d) ->
      d.radius = Math.max(5,d.cash/20000)
      d.y = d.coinvestment
      d.date = d3.time.format("%Y-%m-%d").parse(d.date)
    viz.renderBubbleChart(data.bubble,'#graph_bubble',d3.scale.category10())
    # Render pie chart of sector investments
    viz.renderPieChart(data.pie1,'#graph_pie1',viz.sector_color,32,viz.sector_list)
    # Render pie chart of unsecured investments
    known_colors = []
    pie2_color = (x) ->
        index = known_colors.indexOf(x)
        if index==-1
          known_colors.push x
          index = known_colors.indexOf(x)
        if x=='Loans and facilities - Unsecured'
          return d3.rgb('#74C476').brighter 1
        if x=='Loans and facilities - Partially secured'
          return d3.rgb('#74C476')
        return d3.rgb('#193B79').brighter(index/2)
    viz.renderPieChart(data.pie2,'#graph_pie2',pie2_color)

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
viz.sector_color = d3.scale.category20c()
viz.sector_list = []
viz.text_to_css_class = (x) ->
  x.toLowerCase().replace(/[ ]/g,'-').replace(/[^a-z-]/g,'')

viz.legend = (container,elements,colorFunction,trim=-1) ->
    ul = container\
      .append("ul")\
      .attr('class','legend')
    ul.selectAll('li')\
      .data(elements)\
      .enter()\
      .append('li')\
      .attr("class", (d) -> "hoverable hover-"+viz.text_to_css_class(d))\
      .text( (d) -> viz.trim(d,trim) )
      .append('div')\
      .attr('class','swatch')\
      .style('background-color',colorFunction)
