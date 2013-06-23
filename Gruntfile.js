module.exports = function(grunt) {
  path = require('path');

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    concat: {
      options: {
        banner: '/*! DGU+CKAN Application JS concatenated <%= grunt.template.today("yyyy-mm-dd") %> */\n'
      },
      scripts: {
        src: [ /* Order of resources is important */
          'ckanext/dgu/theme/public/scripts/dgu.js',
          'ckanext/dgu/theme/public/scripts/dgu-basket.js',
          'ckanext/dgu/theme/public/scripts/dgu-autocomplete.js'
        ],
        dest: 'ckanext/dgu/theme/public/scripts/dgu-compiled.unmin.js'
      },
      styles: {
        src: [  /* Order of resources is important. */
          'ckanext/dgu/theme/less/elements.less',
          'ckanext/dgu/theme/less/dgu-main.less',
        ],
        dest: 'ckanext/dgu/theme/public/css/dgu.less'
      }
    },
    uglify: {
      options: {
        banner: '/*! DGU+CKAN Application JS minified <%= grunt.template.today("yyyy-mm-dd") %> */\n'
      },
      build: {
        src: 'ckanext/dgu/theme/public/scripts/dgu-compiled.unmin.js',
        dest: 'ckanext/dgu/theme/public/scripts/dgu-compiled.js'
      }
    },
    less: {
      options: {
        banner: '/* DGU+CKAN stylesheet compiled <%= grunt.template.today("yyyy-mm-dd") %> */\n',
        yuicompress: true
      },
      build: {
        src: 'ckanext/dgu/theme/public/css/dgu.less',
        dest: 'ckanext/dgu/theme/public/css/dgu.css'
      }
    },
    watch: {
      styles: {
        files: 'ckanext/dgu/theme/less/*',
        tasks: 'styles'
      },
      scripts: {
        files: 'ckanext/dgu/heme/public/scripts/*',
        tasks: 'scripts'
      }
    },
    /*
    imagemin: {
      build: {
        options: { 
          optimizationLevel: 3
        },
        files: [
          {
            expand: true,
            src: '*.jpg',
            cwd: 'assets/src/img/',
            dest: 'assets/img/'
          },
          {
            expand: true,
            src: '*.png',
            cwd: 'assets/src/img/',
            dest: 'assets/img/'
          }
        ]
      },
    },
    */
    timestamp: {
      build: {
        dest: 'ckanext/dgu/theme/timestamp.py'
      }
    }
  });

  grunt.registerMultiTask('timestamp', 'Write timestamp to a file', function(myName, myTargets) {
    grunt.file.write(this.files[0].dest, 'asset_build_timestamp='+Date.now());
  });

  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Default task(s).
  grunt.registerTask('styles', ['concat:styles','less:build','timestamp']);
  grunt.registerTask('scripts', ['concat:scripts','uglify:build','timestamp']);
  grunt.registerTask('default', ['styles','scripts','imagemin','timestamp']);
};
