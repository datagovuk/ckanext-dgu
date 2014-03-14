window.viz ?= {}

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
  d3.json "/scripts/json/social_investments_and_foundations/pandas_graphs.json", (data) ->
    # Initialise sector colors
    data.pie1['all'].forEach (x) -> 
      viz.sector_color x.name
      viz.sector_list.push x.name
    graph_sankey = new viz.Sankey "#social_investment_sankey",data.sankey
    graph_stackedBar = new viz.StackedBarChart '#graph_yearonyear', data.bar.all
    graph_coinvestmentTotal = new viz.CashTotal '#coinvestment-total', data.coinvestment_total
    graph_investmentTotal = new viz.CashTotal '#investment-total', data.investment_total['all']
    graph_sunburst = new viz.Sunburst '#social_investment_coinvestment', data.sunburst
    graph_pie1 = new viz.PieChart('#graph_pie1',data.pie1['all'],viz.sector_color,{trimLegend:32, legendData:viz.sector_list})
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
window.viz.loadInvestmentReadiness = ->
    d3.json '/scripts/json/investment-readiness-programme/investment-readiness-d3.json', (data) ->
        new viz.Headline(d3.select('#icrf_headline1'), data.icrf_mean, 'mean investment', money=true)
        new viz.Headline(d3.select('#icrf_headline2'), data.icrf_count, 'organisations funded')
        new viz.MoneyLine(d3.select('#icrf_cash'), data.icrf_items)
        d3.select('#icrf_map').html('(map goes here)')
        vizTable = new viz.SibTable('#sib_table',data.sib)
        #vizTable.on('viz.selectRow', (x)->console.log(x))
        window.data = data
        sector_legend = []
        # -- pie chart setup
        color1 = d3.scale.category20()
        color2 = d3.scale.category20()
        for i in [1..8]
            color2('x'+i)
        piechart_options = { width:170, height: 190, innerRadius:0,radius:85,trimLegend:35,legend:true}
        # DOM building and bniding
        graph_pie1 = new viz.PieChart('#sib_pie1',data.sib[0].sector_pie,color1,piechart_options)
        graph_pie2 = new viz.PieChart('#sib_pie2',data.sib[0].target_pie,color2,piechart_options)
        rowz = d3.select('#sib_table').selectAll('.sib_row')
        rowz.each((data,index)-> @onclick = ((event) ->
            rowz.classed('active',(dd,ii)->ii==index)
            graph_pie1.setData(data.sector_pie)
            graph_pie2.setData(data.target_pie)
            d3.selectAll('#sib_container .venturename').text(data.name)
        ))
        rowz.on('click',(event) ->
            @onclick(event)
            #window.clearInterval(window.sib_interval)
        )
        d3.select(rowz[0][0]).classed('active',true)
        n=1
        #window.sib_interval = window.setInterval((->rowz[0][n++%4].onclick()),1800)
        ## Hack in some tooltips for the sector icons
        d3.selectAll('#sib_container .icon').each (d)->
            text = data.icon_to_sector[d]
            $(@).tooltip({title:text,placement:'bottom'})
        # (jQuery hack) Bind to all hoverable elements
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
                    el.addClass 'hovering'
                  else
                    el.css('fill',el.attr('data-col1') )
                    el.css('stroke','none' )
                    el.removeClass 'hovering'
                  if el.is('circle')
                    el.css('opacity',1)




class viz.MoneyLine
    constructor: (@domElement, @items) ->
        @domElement.style('position','relative')
        @mouseOverBox = @domElement.append('div')
            .classed('moneyline_mouseover',true)
        @container = @domElement.append('div')
            .classed('moneyline',true)
        @container.append('div').classed('bg',true)
        min = d3.min(@items, (d)->d.amount)*0.95
        max = d3.max(@items, (d)->d.amount)*1.05
        point_color = d3.interpolateRgb('#5c5','#00f')
        @points = @container.selectAll('.point')
            .data(@items)
            .enter()
            .append('div')
            .classed('point',true)
            .style('left',(d) -> ((d.amount-min)*100)/(max-min)+'%')
            .style('background',(d)->point_color (d.amount-min)/(max-min))
        @container.append('div')
            .classed('min',true)
            .html('£'+viz.money_to_string(Math.floor(min)))
        @container.append('div')
            .classed('max',true)
            .html('£'+viz.money_to_string(Math.ceil(max)))
        @container.on 'mousemove', @onMouseMove
        @domElement.on 'mouseout', @onMouseOut
        # Store some precomputed values for elegance and speed
        @containerBounds = containerBounds = @container[0][0].getBoundingClientRect()
        @points.each -> @myLeft=@getBoundingClientRect().left-containerBounds.left
        @container.append('div')
          .classed('moneyline_hint',true)
          .html('Who has received investments?<br/>Point your mouse for details.')

    onMouseMove: =>
        left = d3.mouse(@container[0][0])[0]
        lit = []
        @points.classed 'active', (d)-> 
            if Math.abs(left-@myLeft) < 8
                lit.push d
                return true
        if lit.length
            lit.sort (a,b)->a.amount-b.amount
            html = lit.map (x) ->
                    link = if x.url then "<a href=\"#{x.url}\">#{x.name}</a>" else x.name
                    return "<div class=\"entry\">#{link} <b>£#{viz.money_to_string(x.amount)}</b></div>" 
                .join('<hr/>')
            max_w = @containerBounds.width - 250
            @mouseOverBox.html(html)
                .style('left', Math.max(0, Math.min(max_w, left-125))+'px')
                .style('display','block')
        else
            @mouseOverBox.style('display','none')

    onMouseOut: =>
        @points.classed 'active', false
        @mouseOverBox.style('display','none')


class viz.SibTable
    constructor: (@selector, @data) ->
        table = d3.select @selector
        row = table.selectAll('div.sib_row')
            .data(@data)
            .enter()
            .append('div')
            .classed('sib_row',true)
        row.append('div')
            .classed('name',true)
            .html((d)->"<img src=\"#{d.img}\"/>")
            # .html((d)->"<a href=\"#{d.url}\"><img src=\"#{d.img}\"/></a>")
        row.each (d) -> new viz.Headline( d3.select(@).append('div').classed('funding',true), d.total_funding, 'Total Funding', true)
        row.each (d) -> new viz.Headline( d3.select(@).append('div').classed('mean',true), d.mean_investment, 'Mean Investment', true)
        row.append('div')
            .classed('investments',true)
            .html((d) ->"<div class=\"prefix\">Investment Ventures (#{d.investment_sectors.length}): </div>")
            .selectAll('i')
            .data( (d)->d.investment_sectors)
            .enter()
            .append('i')
            .classed('icon',true)
            .each((d) -> @className+=' '+d )

class viz.Headline
    constructor: (@domElement, top, bottom, money=false) ->
        if top==-1
            top = '<span class="unknown">(unknown)</span>'
        else if money
            top = '<span class="poundsign">£</span>'+viz.money_to_string(top)
        @container = @domElement.append('div')
            .classed('headline',true)
        @container.append('div')
            .classed('top',true)
            .html(top)
        @container.append('div')
            .classed('bottom',true)
            .html(bottom)


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
viz.uniqueClassGenerator = (prefix="unique") ->
  known = {}
  latest = 0
  return (x) ->
    if not (x of known)
      out = prefix+(latest++)
      known[x] = out
    return known[x]
viz.shallowCopy = (object) ->
  out = {}
  for k,v of object
    out[k] = v
  return out

d3.selection.prototype.moveToBack = ->
    @each ->
        firstChild = @parentNode.firstChild
        if (firstChild) then @parentNode.insertBefore(this, firstChild)

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


window.viz.loadOrganograms = ->
  d3.json "/scripts/json/organograms/organograms/graph.json", (root) ->
    organogram_graph = new viz.organogram(root)


class window.viz.organogram
  width: 940
  height: 800
  radius: 270
  pw: 130
  ph: 14
  # OrgChart: Redistribute y values to cluser around the core
  offset: (y) => (y*y)/@radius 
  color: d3.scale.category20c()

  constructor: (raw_root)->
    @orgChart = @buildOrgChart(raw_root,'','root')
    @treeMap = @buildTreeMap(@orgChart)
    @container = d3.select('#organogram-viz')
    @svg = d3.select('#organogram-viz')
      .append('svg')
      .attr('width',@width)
      .attr('height',@height)
      .append('g')
      .attr('transform',"translate(#{@width/2},#{@height/2})")
    @defs = @svg.append('defs')
    # Initial state
    @renderOrgChart(intro=true)
    # Bind interactive elements
    btnz = d3.selectAll('.organogram-button')
    btnz.on 'click',(_x,index)=>
      btnz.classed('active',(_x,i)->i==index)
      if index==0 then @renderOrgChart() else @renderTreeMap()
    @hoverBox = @container.append('div')
      .classed('hoverbox',true)

  # Recursive function
  buildOrgChart: (d, parentId, myId) =>
    out = {
      original : d
      name     : if d.senior then d['Job Title'] else d['Generic Job Title']
      value    : if d.senior then d['Actual Pay Floor (£)'] else d['Payscale Minimum (£)']
      key      : myId
      group    : parentId
      isLeaf   : true
    }
    if (d.children and d.children.length) 
      out.isLeaf   = false
      out.group    = myId
      out.children = ( @buildOrgChart(child,myId,"#{myId}.#{i}") for child,i in d.children )
    return out

  # Bizarre behaviour of the D3 Treemap engine means
  # I have to create a shallow copy of the entire tree
  # with a /subtly/ different structure...!
  buildTreeMap: (d) =>
    if not d.children then return d
    out =
      key: "tmp-#{d.key}"
      children: []
    myself = viz.shallowCopy d
    myself.children = undefined
    out.children.push myself
    for child in d.children
      out.children.push @buildTreeMap(child)
    return out

  hoverPerson: =>
    parent = this
    return (d,i) ->
      window.clearTimeout window.viz.organogram_hover_timeout
      if parent.hovering == d.original
        return
      parent.hovering = d.original
      w     = 280
      space = 20
      bbox        = @.getBoundingClientRect()
      bbox_parent = parent.container[0][0].getBoundingClientRect()
      if (bbox.left-bbox_parent.left+bbox.width/2) > (bbox_parent.width/2)
        left = bbox.left - bbox_parent.left - w - space
      else
        left = bbox.left - bbox_parent.left + bbox.width + space
      left = Math.max(0,Math.min(bbox_parent.width-w,left))
      top = bbox.top - bbox_parent.top + bbox.height/2 - (if d.original.senior then 100 else 50)
      top = Math.max(-50,Math.min(bbox_parent.height-100,top))
      parent.hoverBox.style(
        display:'block'
        left:Math.round(left)+'px'
        top:Math.round(top)+'px'
      )
      #email_link = (x) -> if '@' not in x then x else "<a href=\"mailto:#{x}\">#{x}</a>"
      email_link = (x) -> x
      if d.original.senior
        parent.hoverBox.html "
          <table class=\"table table-bordered table-condensed\">
            <tr><td>Job&nbsp;Title</td><td>#{d.original['Job Title']}</td></tr>
            <tr><td>Unit</td><td>#{d.original['Unit']}</td></tr>
            <tr><td>Group</td><td>#{d.original['Professional/Occupational Group']}</td></tr>
            <tr><td>Salary</td><td>£#{viz.money_to_string(d.original['Actual Pay Floor (£)'])} - £#{viz.money_to_string(d.original['Actual Pay Ceiling (£)'])}</td></tr>
            <tr><td>Type</td><td><em>Senior Civil Servant</em></td></tr>
            <tr><td colspan=\"2\" style=\"text-align: left;font-weight:normal;font-style:italic;\">#{d.original['Job/Team Function']}</td></tr>
            <tr><td>Name</td><td>#{d.original['Name']}</td></tr>
            <tr><td>Grade</td><td>#{d.original['Grade']}</td></tr>
            <tr><td>#&nbsp;Roles</td><td>#{d.original['FTE']} (full-time equivalent)</td></tr>
            <tr><td>Phone</td><td>#{d.original['Contact Phone']}</td></tr>
            <tr><td>Email</td><td>#{email_link(d.original['Contact E-mail'])}</td></tr>
          </table>"
      else
        parent.hoverBox.html "
          <table class=\"table table-bordered table-condensed\">
            <tr><td>Job&nbsp;Title</td><td>#{d.original['Generic Job Title']}</td></tr>
            <tr><td>Unit</td><td>#{d.original['Unit']}</td></tr>
            <tr><td>Group</td><td>#{d.original['Professional/Occupational Group']}</td></tr>
            <tr><td>Salary</td><td>£#{viz.money_to_string(d.original['Payscale Minimum (£)'])} - £#{viz.money_to_string(d.original['Payscale Maximum (£)'])}</td></tr>
            <tr><td>Type</td><td><em>Junior Civil Servant</em></td></tr>
            <tr><td>Grade</td><td>#{d.original['Grade']}</td></tr>
            <tr><td>#&nbsp;Roles</td><td>#{d.original['Number of Posts in FTE']} (full-time equivalent)</td></tr>
          </table>"

  hoverPersonOut: (d,i) =>
    window.clearTimeout window.viz.organogram_hover_timeout
    @hovering = null
    window.viz.organogram_hover_timeout = window.setTimeout (=>@hoverBox.style('display','none')), 300

  linkPath: (d) =>
    # Lines between boxes
    @linkline ?= d3.svg.line().interpolate('basis')
    sx = (d.source.x-90) * Math.PI / 180
    sy = @offset(d.source.y)
    tx = (d.target.x-90) * Math.PI / 180
    ty = @offset(d.target.y)
    # Lots of aesthetic tweaks...
    if sy==0 then sx = tx    # Align angles or the central node
    point = (angle,offset) -> [ Math.cos(angle)*offset, Math.sin(angle)*offset ]
    return @linkline [
      point(sx,sy),
      point(sx,sy+80),
      point(tx,ty-40),
      point(tx,ty)
    ]

  setData: (persons,links) =>
    clippath_selection = @defs.selectAll('.clipRect')
      .data(persons, key = (d)->d.key)
    clippath_selection.exit().remove()
    clippath_selection.enter().append('clipPath')
      .classed('clipRect',true)
      .attr('id',(d)->d.key)
      .append('rect')
      .attr('width',@pw)
      .attr('height',@ph)
    # -- Links
    link_selection = @svg.selectAll(".link")
      .data(links,key=(d)->d.target.key)
    link_selection.exit().transition().duration(500).style('opacity',0).remove()
    link_selection.enter().append("path")
      .classed("link", true)
      .attr('fill','none')
      .attr('stroke','rgba(0,0,0,0.2)')
      .attr("d", @linkPath)
      .style('opacity',0)
      .moveToBack()
    # -- Persons
    bgcol = (d) =>
      out = d3.rgb( @color d.group )
      if d.isLeaf then out else out.darker(0.6)
    invertText = (d) -> d3.hsl(bgcol(d)).l < 0.7
    person_selection = @svg.selectAll('.person')
      .data(persons, key=(d)->d.key)
    person_selection.exit().remove()
    g_enter = person_selection.enter().append('g')
      .classed('person',true)
      .attr('clip-path',(d)->"url(##{d.key})")
      #.style('opacity',0)
    g_enter.append('rect')
      .style('display', (d)-> if d.name then 'inline' else 'none')
      .attr('fill',bgcol)
      .on('mouseover',@hoverPerson())
      .on('mouseout',@hoverPersonOut)
    g_enter.append('text')
      .style('display', (d)-> if d.name then 'inline' else 'none')
      .classed('invertText',invertText)
      .attr('dx','2px')
      .attr('dy','1.2em')
      .style('font-size','9px')
      .text((d)->d.name)
    g_enter.append('text')
      .style('display', (d)->if d.name then 'inline' else 'none')
      .classed('invertText',invertText)
      .attr('dx','2px')
      .attr('dy','2.4em')
      .style('font-size','9px')
      .text( (d) -> if not d.name then null else '£'+viz.money_to_string(d.value))

  renderOrgChart: (intro=false) =>
    orgLayout = d3.layout.cluster().size([360,@radius])
    nodes = orgLayout.nodes(@orgChart)
    ripple = (d,i) =>
      i = nodes.length-i
      return i*14
    duration = 500
    if intro
      duration = 0
      ripple = -> 0
    @setData nodes, orgLayout.links(nodes)
    @svg.selectAll(".link").transition()
      .transition()
      .duration(duration*5)
      .delay(if intro then 0 else 1000)
      .style('opacity',1)
    @svg.selectAll('.person')
      .attr('display','inline')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('transform', (d) =>
        if d.y==0 then  return "translate(#{-@pw/2},#{-@ph/2})"
        if d.x<180 then return "translate(0,#{-@ph/2})rotate(#{d.x-90},0,#{@ph/2})translate(#{@offset(d.y)})"
        else            return "translate(0,#{-@ph/2})rotate(#{d.x-270},0,#{@ph/2})translate(#{-@offset(d.y)-@pw})"
      )
    @svg.selectAll('.person').select('rect')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',@pw)
      .attr('height',@ph)
    @svg.selectAll('.clipRect').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',@pw)
      .attr('height',@ph)

  renderTreeMap: =>
    treemap = d3.layout.treemap()
      .size([@width,@height])
      .sticky(true)
      .value( (d) -> d.value )
    nodes = treemap.nodes(@treeMap)
    groups = []
    for node in nodes
      if groups.indexOf(node.group) < 0 then groups.push node.group
    @setData nodes, []
    # --
    duration = 500
    ripple  = (d,i) =>
      return i*14
      index = groups.indexOf(d.group)
      return (index%(groups.length)) * 260
    # --
    @svg.selectAll('.person')
      .attr('display',(d)->if d.value then 'inline' else 'none')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('transform',(d)=>"translate(#{d.x-@width/2},#{d.y-@height/2})")
    @svg.selectAll('.person').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',(d)->d.dx)
      .attr('height',(d)->d.dy)
    @svg.selectAll('.clipRect').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',(d)->Math.max(0,d.dx-1))
      .attr('height',(d)->Math.max(0,d.dy-1))
