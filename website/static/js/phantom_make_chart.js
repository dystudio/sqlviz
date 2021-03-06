var webPage = require('webpage');
var page = webPage.create();
var system = require('system');
var args = system.args;
page.includeJs('http://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js', function() {
  if (page.injectJs('/make_chart.js')) {
    var data = JSON.parse(args[1]);
    //console.log(data.columns);
    //console.log(data.data);
    //console.log(data.stacked);
    var options = page.evaluate(function(data) {
      // returnTitle is a function loaded from our do.js file - see below
      return make_chart(data.columns,data.data,'',data.stacked,data.chart_type,data.title,data.xAxis,data.yAxis,data.yAxis_log,data.defaults);
      //columns, data, target, stacked, graph_type, title, xAxis, yAxis, yAxis_log, defaults);
    }, data);
    options = JSON.stringify(options);
    var fs = require('fs');
    var path = args[2];
    fs.write(path, options, 'w');

    //console.log(options);
    phantom.exit();
  }
});
