module.exports = function(grunt) {
  var pkg = grunt.file.readJSON('package.json');

  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-coffee');

  // Change relative directory
  grunt.file.setBase('ckanext/dgu/theme/');

  // Project configuration.
  grunt.initConfig({
    pkg: pkg,
    uglify: {
      //options: { beautify: true, mangle: false, compress: false, }, //  <-- DEBUG MODE
      app: {
        files:  {
          'public/scripts/dgu-ckan-application.min.js' : [ 'src/scripts/dgu.js', 'src/scripts/dgu-basket.js', 'src/scripts/dgu-autocomplete.js' ],
          'public/scripts/dgu-dataset-map.min.js'          : 'src/scripts/dgu-dataset-map.js',
          'public/scripts/dgu-history.min.js'              : 'src/scripts/dgu-history.js',
          'public/scripts/dgu-package-form.min.js'         : 'src/scripts/dgu-package-form.js',
          'public/scripts/dgu-package.min.js'              : 'src/scripts/dgu-package.js',
          'public/scripts/dgu-publisher-forms.min.js'      : 'src/scripts/dgu-publisher-forms.js',
          'public/scripts/dgu-publisher-index.min.js'      : 'src/scripts/dgu-publisher-index.js',
          'public/scripts/dgu-publisher-read.min.js'       : 'src/scripts/dgu-publisher-read.js',
        },
      },
      vendor: {
        files: {
          'public/scripts/vendor/jquery.tablesorter.min.js'   : 'src/scripts/vendor/jquery.tablesorter.js',
          'public/scripts/vendor/jquery.jstree.min.js'        : 'src/scripts/vendor/jquery.jstree.js',
          'public/scripts/vendor/jquery-ui-1.9.2.custom.datepicker.min.js'        : 'src/scripts/vendor/jquery-ui-1.9.2.custom.datepicker.js',
          'public/scripts/vendor/d3.v3.min.js'                : 'src/scripts/vendor/d3.v3.js',
          'public/scripts/vendor/d3.sankey.min.js'            : 'src/scripts/vendor/d3.sankey.js',
        },
      },
      recline: {
        src: [
          'src/scripts/recline_pack/underscore-1.1.6.js',
          'src/scripts/recline_pack/backbone-0.5.1.js',
          'src/scripts/recline_pack/jquery.mustache.js',
          'src/scripts/recline_pack/jquery.flot-0.7.js',
          'src/scripts/recline_pack/recline.js',
          'src/scripts/recline_pack/dgu-recline-integration.js',
        ],
        dest: 'public/scripts/dgu-recline-pack.min.js',
      },

    },
    less: {
      options: {
        yuicompress: true
      },
      build: {
        src: 'src/css/dgu-ckan.less',
        dest: 'public/css/dgu-ckan.min.css'
      },
      viz: {
        src: 'src/css/dgu-viz.less',
        dest: 'public/css/dgu-viz.min.css',
      },
      datepicker: {
        src: 'src/css/jquery-ui-1.9.2.custom.datepicker.css',
        dest: 'public/css/jquery-ui-1.9.2.custom.datepicker.min.css',
      },
      recline: {
        src: [ 
          'src/css/recline_pack/recline-data-explorer.min.css',
          'src/css/recline_pack/recline-grid.css',
          'src/css/recline_pack/dgu-recline-integration.css',
        ],
        dest: 'public/css/dgu-recline-pack.min.css'
      }
    },
    watch: {
      json: { 
        files: 'src/scripts/json/**/*.json',
        tasks: 'copy:json'
      },
      styles: {
        files: 'src/css/**/*',
        tasks: 'styles'
      },
      scripts: {
        files: 'src/scripts/dgu*.js',
        tasks: 'uglify:app'
      },
      coffee: {
        files: 'src/scripts/**/*.coffee',
        tasks: 'coffee'
      },
    },
    imagemin: {
      build: {
        options: { 
          optimizationLevel: 3
        },
        files: [
          {
            expand: true,
            src: '**/*.{jpg,png}',
            cwd: 'src/images/',
            dest: 'public/images/'
          }
        ]
      },
    },
    copy: {
      images: {
        expand: true,
        cwd: 'src/images/',
        src: '**/*.gif',
        dest: 'public/images/',
      },
      json: {
        expand: true,
        cwd: 'src/scripts/json/',
        src: '**/*.json',
        dest: 'public/scripts/json/',
      },
    },
    coffee: {
      viz_pack: {
        src: [
          'src/scripts/viz_pack/viz_lib/*.coffee',
          'src/scripts/viz_pack/dgu-viz.coffee',
        ],
        dest: 'public/scripts/dgu-viz-pack.min.js'
      }
    },
    timestamp: {
      build: {
        dest: 'timestamp.py'
      }
    }
  });

  grunt.registerMultiTask('timestamp', 'Write timestamp to a file', function(myName, myTargets) {
    grunt.file.write(this.files[0].dest, 'asset_build_timestamp='+Date.now());
  });
  // Default task(s).
  grunt.registerTask('styles', ['less','timestamp']);
  grunt.registerTask('scripts', ['uglify:app','timestamp','coffee']);
  grunt.registerTask('images', ['imagemin','copy:images','timestamp']);
  grunt.registerTask('default', ['uglify','coffee','less','imagemin','copy','timestamp']);
};
