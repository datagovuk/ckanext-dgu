module.exports = function(grunt) {
  path = require('path');

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    uglify: {
      app: {
        src: [
          'ckanext/dgu/theme/src/scripts/dgu.js',
          'ckanext/dgu/theme/src/scripts/dgu-basket.js',
          'ckanext/dgu/theme/src/scripts/dgu-autocomplete.js'
          ],
        dest: 'ckanext/dgu/theme/public/scripts/dgu-ckan-application.min.js'
      },
      openspending: {
        src: [
          'ckanext/dgu/theme/src/scripts/openspending_pack/base64.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/accounting-0.3.2.min.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/underscore-1.2.0.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/handlebars-1.0.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/openspending.boot.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/openspending.utils.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/jquery.datatables-1.9.0.min.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/datatables.bootstrap.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/openspending.data_table.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/openspending.faceter.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/openspending.browser.js',
          'ckanext/dgu/theme/src/scripts/openspending_pack/dgu_openspending_integration.js',
        ],
        dest: 'ckanext/dgu/theme/public/scripts/dgu-openspending-pack.min.js'
      }
    },
    less: {
      build: {
        src: 'ckanext/dgu/theme/src/css/dgu-ckan.less',
        dest: 'ckanext/dgu/theme/public/css/dgu-ckan.min.css'
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
        src: '**/*.{gif}',
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

  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Default task(s).
  grunt.registerTask('styles', ['less:build','timestamp']);
  grunt.registerTask('scripts', ['copy:scripts','uglify:app','timestamp']);
  grunt.registerTask('images', ['imagemin','copy:images','timestamp']);
  grunt.registerTask('default', ['copy','styles','scripts','images','timestamp']);
};
