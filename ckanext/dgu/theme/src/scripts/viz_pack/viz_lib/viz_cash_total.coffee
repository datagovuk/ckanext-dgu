window.viz ?= {}

class viz.CashTotal
  constructor: (@selector,data) ->
    @setData data

  setData: (data) =>
    d3.select(@selector)
      .data([data])
      .html((d)->'<span class="poundsign">£</span>'+viz.money_to_string(data))
      .style('color','white')
      .transition().duration(500).delay(100)
      .style('color','black')
    #.transition().duration(1000).delay(200)
    #console.log 

