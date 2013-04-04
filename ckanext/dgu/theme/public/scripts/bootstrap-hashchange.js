/* ========================================================
 * bootstrap-hashtab.js v1.0.0
 * ========================================================
 * Based on bootstrap-tab.js.
 * Written by Tom Rees. 
 *  * http://zephod.com
 *  * http://github.com/zephod
 * Custom plugin for handling data-toggle="hashtab".
 * Works exactly like data-toggle="tab" but I respond to
 * hashchange events.  Page state is memo-ized in the URL.
 * ======================================================== */


!function ($) {

  "use strict"; // jshint ;_;


 /* HASHTAB CLASS DEFINITION
  * ==================== */

  var HashTab = function (element) {
    this.element = $(element)
  }

  HashTab.prototype = {

    constructor: HashTab

  , show: function () {
      var $this = this.element
        , $ul = $this.closest('ul:not(.dropdown-menu)')
        , selector = $this.attr('data-target')
        , previous
        , $target
        , e

      if (!selector) {
        selector = $this.attr('href')
        selector = selector && selector.replace(/.*(?=#[^\s]*$)/, '') //strip for ie7
      }

      if (selector.substr(0,1)=='#') {
        window.location.hash = 'tab-'+selector.substr(1);
      }

      if ( $this.parent('li').hasClass('active') ) return

      previous = $ul.find('.active:last a')[0]

      e = $.Event('show', {
        relatedTarget: previous
      })

      $this.trigger(e)

      if (e.isDefaultPrevented()) return

      $target = $(selector)

      this.activate($this.parent('li'), $ul)
      this.activate($target, $target.parent(), function () {
        $this.trigger({
          type: 'shown'
        , relatedTarget: previous
        })
      })
    }

  , activate: function ( element, container, callback) {
      var $active = container.find('> .active')
        , transition = callback
            && $.support.transition
            && $active.hasClass('fade')

      function next() {
        $active
          .removeClass('active')
          .find('> .dropdown-menu > .active')
          .removeClass('active')

        element.addClass('active')

        if (transition) {
          element[0].offsetWidth // reflow for transition
          element.addClass('in')
        } else {
          element.removeClass('fade')
        }

        if ( element.parent('.dropdown-menu') ) {
          element.closest('li.dropdown').addClass('active')
        }

        callback && callback()
      }

      transition ?
        $active.one($.support.transition.end, next) :
        next()

      $active.removeClass('in')
    }
  }


 /* HASHTAB PLUGIN DEFINITION
  * ===================== */

  var old = $.fn.hashtab

  $.fn.hashtab = function ( option ) {
    return this.each(function () {
      var $this = $(this)
        , data = $this.data('hashtab')
      if (!data) $this.data('hashtab', (data = new HashTab(this)))
      if (typeof option == 'string') data[option]()
    })
  }

  $.fn.hashtab.Constructor = HashTab


 /* HASHTAB NO CONFLICT
  * =============== */

  $.fn.hashtab.noConflict = function () {
    $.fn.hashtab = old
    return this
  }


 /* TAB DATA-API
  * ============ */

  $(document).on('click.tab.data-api', '[data-toggle="hashtab"], [data-toggle="hashpill"]', function (e) {
    e.preventDefault();
    var disabled = $(this).attr('disabled') == 'disabled';
    if (!disabled) { $(this).hashtab('show') }
  })

  /* HANDLE HASH CHANGES
   * =================== */
  $(function() {
    // Triggered when links are clicked, or browser 'back' fires...
    $(window).hashchange(function() {
      var hash = window.location.hash;
      if (hash.substr(0,5)=='#tab-') {
        var href = '#'+hash.substr(5);
        var link = $('a[data-toggle="hashtab"][href="'+href+'"]');
        var disabled = link.attr('disabled') == 'disabled';
        if (!disabled) { link.hashtab('show'); }
      }
    });
    // Handle initial state
    $(window).trigger('hashchange');
  });

}(window.jQuery);

/*
 * jQuery hashchange event - v1.3 - 7/21/2010
 * http://benalman.com/projects/jquery-hashchange-plugin/
 * 
 * Copyright (c) 2010 "Cowboy" Ben Alman
 * Dual licensed under the MIT and GPL licenses.
 * http://benalman.com/about/license/
 */
(function($,e,b){var c="hashchange",h=document,f,g=$.event.special,i=h.documentMode,d="on"+c in e&&(i===b||i>7);function a(j){j=j||location.href;return"#"+j.replace(/^[^#]*#?(.*)$/,"$1")}$.fn[c]=function(j){return j?this.bind(c,j):this.trigger(c)};$.fn[c].delay=50;g[c]=$.extend(g[c],{setup:function(){if(d){return false}$(f.start)},teardown:function(){if(d){return false}$(f.stop)}});f=(function(){var j={},p,m=a(),k=function(q){return q},l=k,o=k;j.start=function(){p||n()};j.stop=function(){p&&clearTimeout(p);p=b};function n(){var r=a(),q=o(m);if(r!==m){l(m=r,q);$(e).trigger(c)}else{if(q!==m){location.href=location.href.replace(/#.*/,"")+q}}p=setTimeout(n,$.fn[c].delay)}$.browser.msie&&!d&&(function(){var q,r;j.start=function(){if(!q){r=$.fn[c].src;r=r&&r+a();q=$('<iframe tabindex="-1" title="empty"/>').hide().one("load",function(){r||l(a());n()}).attr("src",r||"javascript:0").insertAfter("body")[0].contentWindow;h.onpropertychange=function(){try{if(event.propertyName==="title"){q.document.title=h.title}}catch(s){}}}};j.stop=k;o=function(){return a(q.location.href)};l=function(v,s){var u=q.document,t=$.fn[c].domain;if(v!==s){u.title=h.title;u.open();t&&u.write('<script>document.domain="'+t+'"<\/script>');u.close();q.location.hash=v}}})();return j})()})(jQuery,this);
