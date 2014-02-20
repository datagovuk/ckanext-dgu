$(function() {
  function buildIndex(parentDiv) {
    var out = []
    parentDiv.find('> .publisher').each(function(i,row) {
      row = $(row);
      var link = row.find('> .publisher-row > a:first');
      out.push({
        div        : row,
        link       : link,
        rawtext    : link.text(),
        searchtext : link.text().toLowerCase(),
        children   : buildIndex(row),
      });
    });
    return out;
  }

  var container = $('.publisher-hierarchy');
  var searchBox = $('input#js-search');
  var resultCountBox = $('.result-count');
  var resultCountFooterBox = $('.result-count-footer');
  var index = buildIndex(container);
  assert (container.length);
  assert (searchBox.length);

  /* This is effectively a global variable. I am not proud */
  /* TODO replace with multiple returns from the recursive function 
   * AS LONG AS it doesn't damage performance.  */
  var hacky_count = -1;
  /* Recursive. Runs through a row of the index */
  function updateSearch(searchString) {
    searchString = searchString.toLowerCase();
    if (searchString.length==0 || searchString=='start typing a name...') {
      var p = $('.publisher');
      hacky_count = p.length;
      p.removeClass('match');
      p.removeClass('childMatch');
      container.addClass('empty-search');
      resultCountBox.text(hacky_count);
      resultCountFooterBox.text('Publishers');
      return;
    }
    container.removeClass('empty-search');
    hacky_count = 0;
    for (var i=0;i<index.length;i++) {
      updateSearch_recur(searchString,index[i]);
    }
    resultCountBox.text(hacky_count);
    resultCountFooterBox.text('Results');
  }
  function updateSearch_recur(searchString,entry) {
    var childMatch = false;
    for (var i=0;i<entry['children'].length;i++) {
      childMatch |= updateSearch_recur(searchString,entry['children'][i]);
    }
    var offset = entry['searchtext'].indexOf(searchString);
    if (offset != -1) {
      hacky_count += 1;
      /* light them up */
      var a = entry['rawtext'].substring(0,offset);
      var b = entry['rawtext'].substring(offset,offset+searchString.length);
      var c = entry['rawtext'].substring(offset+searchString.length);
      entry['div'].addClass('match');
      entry['link'].html(a+'<span class="highlight">'+b+'</span>'+c);
      return true;
    }
    /* no match */
    entry['div'].removeClass('match');
    entry['link'].html(entry['rawtext']);
    if (childMatch) {
      entry['div'].addClass('childmatch');
    }
    else {
      entry['div'].removeClass('childmatch');
    }
    return childMatch;
  }


  /* Bind to search box, call updateSearch when stuff gets typed... */
  var cacheVal = '';
  function onChange(e) {
    var val = searchBox.val();
    if (val==cacheVal) { return; }
    cacheVal = val;
    searchBox.addClass('loading');
    window.clearTimeout(window.dgu_pub_timeout);
    window.dgu_pub_timeout = window.setTimeout(function() {
      searchBox.removeClass('loading');
      updateSearch(val);
    }, 200);
  }
  searchBox.on('keydown',onChange);
  searchBox.on('keyup',onChange);
  searchBox.on('keypress',onChange);
  searchBox.change(onChange);
  updateSearch(searchBox.val());

  // -- Init base form
  $('input[name="q"]').focus();
  
  // -- Handle expand/collapse
  $('.js-expand,.js-collapse').click(function(e) {
    e.preventDefault();
    var target = $(e.delegateTarget);
    var expanding = target.hasClass('js-expand');
    target.parent()
      .toggleClass('expanded',expanding)
      .toggleClass('collapsed',!expanding);
    return false;
  });
});
