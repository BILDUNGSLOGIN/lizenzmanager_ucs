//>>built
define('umc/widgets/Page',
    'dojo/_base/declare dojo/_base/kernel dojo/_base/lang dojo/_base/array dojo/dom-class dojox/html/entities umc/tools ../dialog ../render ./Text ./ContainerWidget'.split(
        ' '), function(l, e, m, f, c, d, g, n, h, k, b) {
      return l('umc.widgets.Page', [b], {
        helpText: '',
        helpTextRegion: 'nav',
        helpTextAllowHTML: !0,
        headerText: null,
        headerTextRegion: 'nav',
        headerTextAllowHTML: !1,
        footerButtons: null,
        navButtons: null,
        navContentClass: '',
        mainContentClass: '',
        title: '',
        titleAllowHTML: !1,
        noFooter: !1,
        fullWidth: !1,
        addNotification: function(a, c, b) {n.contextNotify(a, c, b);},
        navBootstrapClasses: 'col-xs-12 col-sm-12 col-md-4 col-lg-4',
        mainBootstrapClasses: 'col-xs-12 col-sm-12 col-md-8 col-lg-8',
        _initialBootstrapClasses: 'col-xs-12 col-sm-12 col-md-12 col-lg-12',
        baseClass: 'umcPage',
        i18nClass: 'umc.app',
        _nav: null,
        _navContent: null,
        _main: null,
        _mainContent: null,
        _footer: null,
        _helpTextPane: null,
        _headerTextPane: null,
        _footerButtons: null,
        _navButtons: null,
        _onShow: function() {},
        _setTitleAttr: function(a) {
          this._set('title', this.titleAllowHTML ?
              a : d.encode(a));
        },
        _setHelpTextAttr: function(a) {
          if (a || this._helpTextPane) {
            if (!this._helpTextPane) {
              this._helpTextPane = new k(
                  {region: this.helpTextRegion, baseClass: 'umcPageHelpText'});
              try {this.addChild(this._helpTextPane, 1);} catch (p) {
                this.addChild(this._helpTextPane);
              }
            }
            c.toggle(this._helpTextPane.domNode, 'dijitDisplayNone', !a);
            this._helpTextPane.set('content',
                this.helpTextAllowHTML ? a : d.encode(a));
            this._set('helpText', a);
          }
        },
        _setHeaderTextAttr: function(a) {
          if (a || this._headerTextPane) this._headerTextPane ||
          (this._headerTextPane =
              new k({
                region: this.headerTextRegion,
                baseClass: 'umcPageHeader',
              }), this.addChild(this._headerTextPane, 0)), c.toggle(
              this._headerTextPane.domNode, 'dijitDisplayNone',
              !a), this._headerTextPane.set('content',
              '\x3ch2\x3e' + (this.headerTextAllowHTML ? a : d.encode(a)) +
              '\x3c/h2\x3e'), this._set('headerText', a);
        },
        _setNavButtonsAttr: function(a) {
          this._set('navButtons', a);
          this._navButtons && (this.removeChild(
              this._navButtons), this._navButtons.destroyRecursive(), this._navButtons = null);
          this.navButtons && (this._navButtons = new b({region: 'nav'}),
              a = h.buttons(this.navButtons), f.forEach(a.$order$,
              m.hitch(this._navButtons, 'addChild')), this.own(
              this._navButtons), this.addChild(this._navButtons));
        },
        postMixInProperties: function() {
          this.inherited(arguments);
          this.fullWidth &&
          (this.mainBootstrapClasses = this.navBootstrapClasses = this._initialBootstrapClasses);
          delete this.attributeMap.title;
        },
        buildRendering: function() {
          this.inherited(arguments);
          this._nav = new b(
              {baseClass: 'umcPageNav', 'class': 'dijitDisplayNone'});
          this._navContent = new b({
            baseClass: 'umcPageNavContent',
            'class': this.navContentClass,
          });
          this._nav.addChild(this._navContent);
          this._main = new b({
            baseClass: 'umcPageMain',
            'class': this._initialBootstrapClasses,
          });
          this._mainContent = new b({
            baseClass: 'umcPageMainContent',
            'class': this.mainContentClass,
          });
          this._main.addChild(this._mainContent);
          b.prototype.addChild.apply(this, [this._nav]);
          b.prototype.addChild.apply(this, [this._main]);
          this._footer = new b({
            region: 'footer',
            baseClass: 'umcPageFooter',
            'class': this._initialBootstrapClasses,
          });
          g.toggleVisibility(this._footer,
              !1);
          b.prototype.addChild.apply(this, [this._footer]);
          this.headerText && this.set('headerText', this.headerText);
          this.helpText && this.set('helpText', this.helpText);
          if (!this.noFooter && this.footerButtons &&
              this.footerButtons instanceof Array &&
              this.footerButtons.length) {
            g.toggleVisibility(this._footer, !0);
            var a = new b({'class': 'umcPageFooterLeft'});
            this._footer.addChild(a);
            var c = new b({'class': 'umcPageFooterRight'});
            this._footer.addChild(c);
            this._footerButtons = h.buttons(this.footerButtons);
            f.forEach(this._footerButtons.$order$,
                function(b) {
                  'submit' == b.type || b.defaultButton || 'right' == b.align
                      ? c.addChild(b)
                      : a.addChild(b);
                }, this);
          }
        },
        addChild: function(a, b) {
          a.region && 'center' != a.region && 'right' != a.region ? 'top' ==
          a.region || 'left' == a.region ? a.region = 'nav' : 'bottom' ==
              a.region && (a.region = 'footer') : a.region = 'main';
          'out' === a.region ? this.inherited(arguments) : 'nav' == a.region
              ? this._navContent.addChild.apply(this._navContent, arguments)
              : 'footer' == a.region ? this._footer.addChild.apply(this._footer,
                  arguments) : this._mainContent.addChild.apply(
                  this._mainContent,
                  arguments);
          this._started && this._adjustSizes();
        },
        getChildren: function(a) {
          if (a) {
            if ('nav' === a) return this._navContent.getChildren();
            if ('main' === a) return this._mainContent.getChildren();
            if ('footer' === a) return this._footer.getChildren();
          } else return this.inherited(arguments);
        },
        addNote: function(a) {
          e.deprecated('umc/widgets/Page:addNote()',
              'use dialog.notify(), dialog.warn(), Module.addNotification(), or Module.addWarning() instead!');
          this.addNotification(a);
        },
        clearNotes: function() {
          e.deprecated('umc/widgets/Page:clearNotes()',
              'remove it, it has no effect!');
        },
        _adjustSizes: function() {
          c.remove(this._nav.domNode);
          c.remove(this._main.domNode);
          c.add(this._nav.domNode,
              this._nav['class'] + ' ' + this._nav.baseClass);
          c.add(this._main.domNode,
              this._main['class'] + ' ' + this._main.baseClass);
          var a = this._navContent.getChildren().length;
          a && (c.toggle(this._nav.domNode, 'dijitDisplayNone', !1), c.remove(
              this._nav.domNode, this._initialBootstrapClasses), c.add(
              this._nav.domNode, this.navBootstrapClasses), c.remove(
              this._main.domNode, this._initialBootstrapClasses),
              c.add(this._main.domNode, this.mainBootstrapClasses));
          a && !this.fullWidth ||
          c.add(this.domNode, this.baseClass + '--fullWidth');
        },
        startup: function() {
          this.inherited(arguments);
          this._adjustSizes();
        },
      });
    });
//# sourceMappingURL=Page.js.map