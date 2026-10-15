const basePath = "babubi/static/babubi/";

const config = {
  basePath: basePath,
  extrasConfig: {
    fonts: {
      dest: basePath + "font/",
      files: "babubi/static_src/fontello/font/*",
    },
    images: {
      dest: basePath + "img/",
      files: "**/static_src/img/**/*",
    },
    logo: {
      dest: basePath + "logo/",
      files: "babubi/static_src/logo/**/*",
    },
    root: {
      dest: basePath + "root/",
      files: "babubi/static_src/root/*",
    },
  },
  glyphFontConfig: {
    configFile: "babubi/static_src/fontello/config.json",
    dest: "babubi/static_src/fontello",
  },
  scriptsConfig: {
    dest: basePath + "js/",
    vendor: [
      "node_modules/pulltorefreshjs/dist/index.umd.js",
      "node_modules/jquery/dist/jquery.js",
      "node_modules/@popperjs/core/dist/umd/popper.js",
      "node_modules/bootstrap/dist/js/bootstrap.js",
      "node_modules/masonry-layout/dist/masonry.pkgd.js",
    ],
    graph: [
      "node_modules/plotly.js/dist/plotly-cartesian.js",
      "node_modules/plotly.js/dist/plotly-locale-ca.js",
      "node_modules/plotly.js/dist/plotly-locale-cs.js",
      "node_modules/plotly.js/dist/plotly-locale-de.js",
      "node_modules/plotly.js/dist/plotly-locale-da.js",
      "node_modules/plotly.js/dist/plotly-locale-es.js",
      "node_modules/plotly.js/dist/plotly-locale-fi.js",
      "node_modules/plotly.js/dist/plotly-locale-fr.js",
      "node_modules/plotly.js/dist/plotly-locale-he.js",
      "node_modules/plotly.js/dist/plotly-locale-hr.js",
      "node_modules/plotly.js/dist/plotly-locale-hu.js",
      "node_modules/plotly.js/dist/plotly-locale-it.js",
      "node_modules/plotly.js/dist/plotly-locale-ko.js",
      "node_modules/plotly.js/dist/plotly-locale-ja.js",
      "node_modules/plotly.js/dist/plotly-locale-no.js",
      "node_modules/plotly.js/dist/plotly-locale-nl.js",
      "node_modules/plotly.js/dist/plotly-locale-pl.js",
      "node_modules/plotly.js/dist/plotly-locale-pt-br.js",
      "node_modules/plotly.js/dist/plotly-locale-pt-pt.js",
      "node_modules/plotly.js/dist/plotly-locale-ru.js",
      "node_modules/plotly.js/dist/plotly-locale-sr.js",
      "node_modules/plotly.js/dist/plotly-locale-sv.js",
      "node_modules/plotly.js/dist/plotly-locale-tr.js",
      "node_modules/plotly.js/dist/plotly-locale-uk.js",
      "node_modules/plotly.js/dist/plotly-locale-zh-cn.js",
      "node_modules/plotly.js/dist/plotly-locale-zh-hk.js",
      "node_modules/plotly.js/dist/plotly-locale-zh-tw.js",
    ],
    app: [
      "babubi/static_src/js/babubi.js",
      "core/static_src/js/*.js",
      "dashboard/static_src/js/*.js",
    ],
    tags_editor: ["babubi/static_src/js/tags_editor.js"],
  },
  stylesConfig: {
    dest: basePath + "css/",
    app: "babubi/static_src/scss/babubi.scss",
    ignore: ["babubi.scss"],
  },
  testsConfig: {
    isolated: ["babubi.tests.tests_views.ViewsTestCase.test_password_reset"],
  },
  watchConfig: {
    scriptsGlob: ["*/static_src/js/**/*.js", "!babubi/static/js/"],
    stylesGlob: ["*/static_src/scss/**/*.scss"],
  },
};

export default config;
