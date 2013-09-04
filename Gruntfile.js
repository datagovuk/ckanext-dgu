module.exports = function(grunt) {
  var pkg = grunt.file.readJSON('package.json');

  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Change relative directory
  grunt.file.setBase('ckanext/dgu/theme/');

  // Project configuration.
  grunt.initConfig({
    pkg: pkg,
    uglify: {
      options: { beautify: true, mangle: false, compress: false, }, // <-- DEBUG MODE
      app: {
        files:  {
          'public/scripts/dgu-ckan-application.min.js' : [ 'src/scripts/dgu.js', 'src/scripts/dgu-basket.js', 'src/scripts/dgu-autocomplete.js' ],
          'public/scripts/dgu-dataset-map.js'          : 'src/scripts/dgu-dataset-map.js',
          'public/scripts/dgu-history.js'              : 'src/scripts/dgu-history.js',
          'public/scripts/dgu-package-form.js'         : 'src/scripts/dgu-package-form.js',
          'public/scripts/dgu-package.js'              : 'src/scripts/dgu-package.js',
          'public/scripts/dgu-publisher-forms.js'      : 'src/scripts/dgu-publisher-forms.js',
          'public/scripts/dgu-publisher-index.min.js'      : 'src/scripts/dgu-publisher-index.js',
          'public/scripts/dgu-publisher.js'            : 'src/scripts/dgu-publisher.js',
        },
      },
      vendor: {
        files: {
          'public/scripts/vendor/jquery.tablesorter.js'   : 'src/scripts/vendor/jquery.tablesorter.js',
          'public/scripts/vendor/jquery.tagcloud.js'      : 'src/scripts/vendor/jquery.tagcloud.js',
          'public/scripts/vendor/jquery.jstree.min.js'    : 'src/scripts/vendor/jquery.jstree.js',
        },
      },
      openspending: {
        src: [
          'src/scripts/openspending_pack/base64.js',
          'src/scripts/openspending_pack/accounting-0.3.2.min.js',
          'src/scripts/openspending_pack/underscore-1.2.0.js',
          'src/scripts/openspending_pack/handlebars-1.0.js',
          'src/scripts/openspending_pack/openspending.boot.js',
          'src/scripts/openspending_pack/openspending.utils.js',
          'src/scripts/openspending_pack/jquery.datatables-1.9.0.min.js',
          'src/scripts/openspending_pack/datatables.bootstrap.js',
          'src/scripts/openspending_pack/openspending.data_table.js',
          'src/scripts/openspending_pack/openspending.faceter.js',
          'src/scripts/openspending_pack/openspending.browser.js',
          'src/scripts/openspending_pack/dgu-openspending-integration.js',
        ],
        dest: 'public/scripts/dgu-openspending-pack.min.js'
      },
      recline: {
        src: [
          'src/scripts/recline_pack/jquery.mustache.js',
          'src/scripts/recline_pack/jquery.flot-0.7.js',
          'src/scripts/recline_pack/recline.js',
          'src/scripts/recline_pack/dgu-recline-integration.js',
        ],
        dest: 'public/scripts/dgu-recline-pack.min.js',
      },

    },
    less: {
      build: {
        src: 'src/css/dgu-ckan.less',
        dest: 'public/css/dgu-ckan.min.css'
      }
    },
    watch: {
      styles: {
        files: 'src/css/**/*',
        tasks: 'styles'
      },
      scripts: {
        files: 'public/scripts/**/*',
        tasks: 'scripts'
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
        src: '**/*.{gif}',
        dest: 'public/images/',
        filter: 'isFile'
      },
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
  grunt.registerTask('styles', ['less:build','timestamp']);
  grunt.registerTask('scripts', ['uglify:app','timestamp']);
  grunt.registerTask('images', ['imagemin','copy:images','timestamp']);
  grunt.registerTask('default', ['uglify','less','imagemin','copy','timestamp']);
};
