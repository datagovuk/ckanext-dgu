module.exports = function(grunt) {
  path = require('path');

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    concat: {
      options: {
        banner: '/*! DGU+CKAN Application JS concatenated by Grunt */\n'
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
          'ckanext/dgu/theme/src/css/elements.less',
          'ckanext/dgu/theme/src/css/dgu-main.less',
        ],
        dest: 'ckanext/dgu/theme/public/css/dgu.less'
      }
    },
    uglify: {
      options: {
        banner: '/*! DGU+CKAN Application JS minified by Grunt */\n'
      },
      build: {
        src: 'ckanext/dgu/theme/public/scripts/dgu-compiled.unmin.js',
        dest: 'ckanext/dgu/theme/public/scripts/dgu-compiled.js'
      }
    },
    less: {
      options: {
        banner: '/* DGU+CKAN stylesheet compiled by Grunt */\n',
        yuicompress: true
      },
      build: {
        src: 'ckanext/dgu/theme/public/css/dgu.less',
        dest: 'ckanext/dgu/theme/public/css/dgu.css'
      }
    },
    watch: {
      styles: {
        files: 'ckanext/dgu/theme/src/css/**/*',
        tasks: 'styles'
      },
      scripts: {
        files: 'ckanext/dgu/theme/public/scripts/**/*',
        tasks: 'scripts'
      },
      scripts: {
        files: 'ckanext/dgu/theme/src/images/**/*',
        tasks: 'images'
      }
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
            cwd: 'ckanext/dgu/theme/src/images/',
            dest: 'ckanext/dgu/theme/public/images/'
          }
        ]
      },
    },
    copy: {
      images: {
        expand: true,
        cwd: 'ckanext/dgu/theme/src/images/',
        src: '**/*.{gif,ico}',
        dest: 'ckanext/dgu/theme/public/images/',
        filter: 'isFile'
      },
      scripts: {
        expand: true,
        cwd: 'ckanext/dgu/theme/src/scripts/',
        src: '**/*',
        dest: 'ckanext/dgu/theme/public/scripts/'
      },
    },
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
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Default task(s).
  grunt.registerTask('styles', ['concat:styles','less:build','timestamp']);
  grunt.registerTask('scripts', ['copy:scripts','concat:scripts','uglify:build','timestamp']);
  grunt.registerTask('images', ['imagemin','copy:images','timestamp']);
  grunt.registerTask('default', ['copy','styles','scripts','images','timestamp']);
};
