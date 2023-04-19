//>>built
define("umc/widgets/Module",
    "dojo/_base/declare dojo/_base/lang dojo/_base/array dojo/topic dojo/aspect dojo/dom-class dojo/dom-geometry dojo/window dojo/on dijit/layout/StackContainer dojox/html/entities umc/render umc/widgets/_ModuleMixin umc/widgets/ContainerWidget umc/widgets/ModuleHeader umc/widgets/StandbyMixin umc/widgets/Icon umc/i18n!".split(" "),
    function (declare, lang, array, topic, aspect, dom_class, dom_geometry, window, on, StackContainer, entities, render, _ModuleMixin, ContainerWidget, ModuleHeader, StandbyMixin, Icon, _) {
    return declare("umc.widgets.Module", [ContainerWidget, _ModuleMixin, StandbyMixin], {
        _top: null, _bottom: null, __container: null, defaultTitle: null,
        selectablePagesToLayoutMapping: null, postMixInProperties: function () {
            this.inherited(arguments);
            this.defaultTitle = this.title;
            this.__container = (new declare([StackContainer, StandbyMixin]))({baseClass: StackContainer.prototype.baseClass + " umcModuleContent", doLayout: !1});
            this.__container.watch("selectedChildWidget", lang.hitch(this, function (a, b, c) {
                this.set(a, c)
            }));
            this.__container.watch("selectedChildWidget", lang.hitch(this, "__refreshButtonVisibility"));
            this.own(aspect.before(this.__container, "addChild", lang.hitch(this, function (a) {
                this._addHeaderButtonsToChild(a);
                a.own(a.watch("headerButtons", lang.hitch(this, function () {
                    this._addHeaderButtonsToChild(a)
                })))
            }), !0));
            this.own(this.watch("closable", lang.hitch(this, function () {
                this._addHeaderButtonsToChild(this.selectedChildWidget)
            })))
        }, resetTitle: function () {
            this.set("title", this.defaultTitle)
        }, _setTitleAttr: function (a) {
            this._set("title", a);
            this._top && this._top.set("title", a)
        }, addBreadCrumb: function (a) {
            a = lang.replace('\x3cspan class\x3d"umcModuleTitleBreadCrumb"\x3e{0}\x3c/span\x3e{1}\x3cspan\x3e{2}\x3c/span\x3e', [this.defaultTitle,
                Icon.asHTMLString("chevron-right", "umcModuleTitleBreadCrumbSeperator umcModuleTitleBreadCrumb"), entities.encode(a)]);
            this.set("title", a)
        }, subTitle: "", _setSubTitleAttr: function (a) {
            this._top.set("subTitle", a);
            this._set("subTitle", a)
        }, buildRendering: function () {
            this.inherited(arguments);
            this._bottom = new ContainerWidget({"class": "umcModuleWrapperWrapper"});
            var a = new ContainerWidget({baseClass: "umcModuleWrapper", "class": "container"});
            a.addChild(this.__container);
            this._bottom.addChild(a);
            this._top = new ModuleHeader({title: this.get("title")});
            this.own(on(this._bottom.domNode,
                "scroll", lang.hitch(this, function (a) {
                    dom_class.toggle(this.domNode, "umcModule--scrolled", 0 < a.target.scrollTop)
                })));
            ContainerWidget.prototype.addChild.apply(this, [this._top]);
            ContainerWidget.prototype.addChild.apply(this, [this._bottom]);
            this.containerNode = this.__container.containerNode
        }, selectChild: function (a, b) {
            return this.__container.selectChild(a, b)
        }, onClose: function () {
            if (this.__container && this.__container.onClose) this.__container.onClose();
            return !0
        }, addChild: function (a, b) {
            return this.__container.addChild(a, b)
        }, removeChild: function (a) {
            return this.__container.removeChild(a)
        },
        _addHeaderButtonsToChild: function (a) {
            var b = [];
            this.closable && b.push({name: "close", label: _("Close"), callback: lang.hitch(this, "closeModule")});
            a.headerButtons && (b = a.headerButtons.concat(b));
            a.$headerButtons$ && (this._top._right.removeChild(a.$headerButtons$), a.$headerButtons$.destroyRecursive(), delete a.$headerButtons$);
            a._headerButtons = null;
            if (b && b.length) {
                b = array.map(b, function (a) {
                    a.class = (a.class || "") + " ucsNormalButton";
                    return a
                });
                var e = new ContainerWidget({"class": "umcModuleHeaderRight__buttons"});
                a.own(e);
                a._headerButtons =
                    render.buttons(b.reverse(), e);
                array.forEach(a._headerButtons.$order$.reverse(), function (b) {
                    e.addChild(a._headerButtons[b.name]);
                    b.on("mouseEnter", function () {
                        dom_class.add(b.domNode, "dijitButtonHover");
                        var a = dom_geometry.getMarginBox(b.containerNode), c = dom_geometry.position(b.focusNode), d = (a.w - c.w) / 2;
                        c = window.getBox().w - c.x;
                        dom_geometry.setMarginBox(b.containerNode, {l: -Math.max(d, a.w - c + 5)})
                    })
                });
                this._top._right.addChild(e, 0);
                a.$headerButtons$ = e;
                e.$child$ = a
            }
            this._started && this.__refreshButtonVisibility()
        }, __refreshButtonVisibility: function () {
            var a = this.__container.get("selectedChildWidget");
            array.forEach(this._top._right.getChildren(), lang.hitch(this, function (b) {
                b.$child$ && dom_class.toggle(b.domNode, "dijitDisplayNone", b.$child$ !== a)
            }))
        }, layout: function () {
            this.__container.layout()
        }, closeModule: function () {
            this.closable && topic.publish("/umc/tabs/close", this)
        }, startup: function () {
            this.__container.startup();
            this.__container.selectedChildWidget && (this.set("selectedChildWidget", this.__container.selectedChildWidget), this.__refreshButtonVisibility());
            this.inherited(arguments)
        }
    })
});
//# sourceMappingURL=Module.js.map