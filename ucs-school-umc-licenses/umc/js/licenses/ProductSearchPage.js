/*
 * Copyright 2021 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define*/

define([
  "dojo/_base/declare",
  "dojo/_base/lang",
  "dojo/dom",
  "dojo/dom-class",
  "dojo/aspect",
  "dojo/on",
  "dojo/mouse",
  "dojo/query",
  "dojo/date/locale",
  "dojox/html/entities",
  "dijit/Tooltip",
  "umc/store",
  "umc/widgets/Page",
  "umc/widgets/Grid",
  "umc/widgets/SearchForm",
  "umc/widgets/Text",
  "umc/widgets/TextBox",
  "put-selector/put",
  "umc/i18n!umc/modules/licenses",
], function (
  declare,
  lang,
  dom,
  domClass,
  aspect,
  on,
  mouse,
  query,
  dateLocale,
  entities,
  Tooltip,
  store,
  Page,
  Grid,
  SearchForm,
  Text,
  TextBox,
  put,
  _
) {
  return declare("umc.modules.licenses.ProductSearchPage", [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    schoolId: null, // required parameter
    moduleFlavor: null, // required parameter
    showChangeSchoolButton: false,

    _grid: null,
    _gridGroup: null,
    _searchForm: null,

    maxUserSum: "-",
    assignedSum: "-",
    expiredSum: "-",
    availableSum: "-",
    userCount: null,

    _setAllocationAttr: function (allocation) {
      this._set("allocation", allocation);
      domClass.remove(this._assignmentText.domNode, "dijitDisplayNone");
      if (allocation.usernames) {
        this.removeChild(this._grid);
        this.removeChild(this._gridGroup);
        const count = allocation.usernames.length;
        const id = this.id + "-tooltipNode";
        const msg = `
				<p>
					${entities.encode(
          count === 1
            ? _("Assign licenses to 1 selected user.")
            : _("Assign licenses to %s selected users.", count)
        )}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_("show selected users"))})
					</span>
				</p>
				<p>
					${entities.encode(
          _("Choose the medium for which you want to assign licenses.")
        )}
				</p>
			`.trim();
        this._assignmentText.set("content", msg);
        const node = dom.byId(id);
        on(
          node,
          "click",
          lang.hitch(this, function (evt) {
            let label = "";
            for (const username of this.allocation.usernames) {
              label += `<div>${entities.encode(username)}</div>`;
            }
            Tooltip.show(label, node);
            evt.stopImmediatePropagation();
            on.once(
              window,
              "click",
              lang.hitch(this, function (event) {
                Tooltip.hide(node);
              })
            );
          })
        );
      } else if (allocation.workgroup || allocation.schoolClass) {
        this.removeChild(this._grid);
        const id = this.id + "-tooltip";
        const msg = `
				<p>
					${entities.encode(_("Assign licenses to selected workgroup/class."))}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_("show selected workgroup/class"))})
					</span>
				</p>
				<p>
					${entities.encode(
          _("Choose the medium for which you want to assign licenses.")
        )}
				</p>
			`.trim();
        this._assignmentText.set("content", msg);
        const node = dom.byId(id);
        on(
          node,
          "click",
          lang.hitch(this, function (evt) {
            let label = "";
            if (
              this.allocation.workgroup &&
              this.allocation.workgroup !== "__all__"
            ) {
              label = `<div>${entities.encode(
                this.allocation.workgroupName
              )}</div>`;
            } else {
              label = `<div>${entities.encode(
                this.allocation.className
              )}</div>`;
            }

            Tooltip.show(label, node);
            evt.stopImmediatePropagation();
            on.once(
              window,
              "click",
              lang.hitch(this, function (event) {
                Tooltip.hide(node);
              })
            );
          })
        );
      }
    },

    parseGroupName: function (inputValue) {
      return inputValue.split(",")[0].slice(3)
    },

    query: function () {
      this.standbyDuring(
        this._searchForm.ready().then(
          lang.hitch(this, function () {
            this._searchForm.submit();
          })
        )
      );
    },

    showUserCount: function () {
      const count = this.userCount
      const id = this.id + "-tooltipNode";
      const msg = `
				<p>
					${entities.encode(
        count === 1
          ? _("Assign licenses to 1 selected user.")
          : _("Assign licenses to %s selected users.", count)
      )}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_("show selected workgroup/class"))})
					</span>
				</p>
				<p>
					${entities.encode(
        _("Choose the medium for which you want to assign licenses.")
      )}
				</p>
			`.trim();
      this._assignmentText.set("content", msg);
      const node = dom.byId(id);
      on(
        node,
        "click",
        lang.hitch(this, function (evt) {
          let label = "";
          if (
            this.allocation.workgroup &&
            this.allocation.workgroup !== "__all__"
          ) {
            label = `<div>${entities.encode(
              this.allocation.workgroupName
            )}</div>`;
          } else {
            label = `<div>${entities.encode(
              this.allocation.className
            )}</div>`;
          }

          Tooltip.show(label, node);
          evt.stopImmediatePropagation();
          on.once(
            window,
            "click",
            lang.hitch(this, function (event) {
              Tooltip.hide(node);
            })
          );
        })
      );
    },

    onBack: function () {
      // event stub
    },

    onProductChosen: function () {
      // event stub
    },

    onProductChosenForSchool: function () {
      // event stub
    },

    onProductChosenForClass: function () {
      // event stub
    },

    onProductChosenForWorkgroup: function () {
      // event stub
    },

    onChangeUsers: function () {
      // event stub
    },

    onChooseDifferentSchool: function () {
      // event stub
    },

    onShowProduct: function (productId) {
      // event stub
    },

    refreshGrid: function (values,resize=false) {
      values.school = this.schoolId;
      if (this.moduleFlavor === "licenses/allocation" && this.allocation) {
        if (this.allocation.usernames) {
          values.licenseType = ["SINGLE", "VOLUME"];
          this._grid.filter(values);
          this.removeChild(this._gridGroup);
          this.addChild(this._grid);
          if (resize) {
            this._grid.resize();
          }
        } else if (this.allocation.workgroup) {
          if (this.allocation.workgroup && this.allocation.workgroup !== "__all__") {
            values.groupName = this.parseGroupName(this.allocation.workgroup)
          }
          if (this.allocation.schoolClass && this.allocation.schoolClass !== "__all__") {
            values.groupName = this.parseGroupName(this.allocation.schoolClass)
          }
          values.licenseType = ["WORKGROUP"];
          this._gridGroup.filter(values)
            .then(() => {
              if (
                this._gridGroup.collection.data[0] &&
                this._gridGroup.collection.data[0].user_count !== null
              ) {
                this._set("userCount", this._gridGroup.collection.data[0].user_count);
                this.showUserCount()
              }
            })
          this.removeChild(this._grid);
          this.addChild(this._gridGroup);
          if (resize) {
            this._gridGroup.resize();
          }
        }
      } else {
        this._grid.filter(values);
      }
    },

    //// lifecycle
    postMixInProperties: function () {
      this.inherited(arguments);
      const headerButtons = [];
      if (this.moduleFlavor === "licenses/allocation") {
        headerButtons.push({
          name: "close",
          label: _("Change user selection"),
          callback: lang.hitch(this, "onChangeUsers"),
        });
      }
      this.headerButtons = headerButtons;
    },

    buildRendering: function () {
      this.inherited(arguments);

      this._assignmentText = new Text({
        region: "nav",
        class: "dijitDisplayNone",
      });

      const widgets = [
        {
          type: TextBox,
          name: "pattern",
          label: "&nbsp;",
          inlineLabel: _("Search licensed media"),
        },
      ];
      this._searchForm = new SearchForm({
        class: "umcUDMSearchForm umcUDMSearchFormSimpleTextBox",
        region: "nav",
        widgets: widgets,
        layout: [["pattern", "submit"]],
        onSearch: lang.hitch(this, function (values) {
          this.refreshGrid(values);
        }),
      });

      const actions = [];
      if (this.moduleFlavor === "licenses/allocation") {
        actions.push({
          name: "edit",
          label: _("Assign licenses"),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: false,
          callback: lang.hitch(this, function (_idxs, products) {
            if (this.allocation.usernames) {
              this.onProductChosen(
                products[0].productId,
                this.allocation.usernames
              );
            } else if (this.allocation.school) {
              this.onProductChosenForSchool(
                products[0].productId,
                this.allocation.school
              );
            } else if (
              this.allocation.schoolClass &&
              this.allocation.schoolClass !== "__all__"
            ) {
              this.onProductChosenForWorkgroup(
                products[0].productId,
                "",
                this.allocation.schoolClass,
                "",
                this.allocation.className,
                this.userCount
              );
            } else if (
              this.allocation.workgroup &&
              this.allocation.workgroup !== "__all__"
            ) {
              this.onProductChosenForWorkgroup(
                products[0].productId,
                this.allocation.workgroup,
                "",
                this.allocation.workgroupName,
                "",
                this.userCount
              );
            }
          }),
        });
      } else {
        actions.push({
          name: "edit",
          label: _("Show details"),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: false,
          callback: lang.hitch(this, function (_idxs, products) {
            this.onShowProduct(products[0].productId);
          }),
        });
      }
      const columns = [
        {
          name: "productId",
          label: _("Medium ID"),
          width: "160px",
          formatter: function (value) {
            if (value && value.startsWith("urn:bilo:medium:")) {
              value = value.slice(16, value.length);
            }
            return value;
          },
        },
        {
          name: "title",
          label: _("Medium"),
          width: "200px",
        },
        {
          name: "publisher",
          label: _("Publisher"),
          width: "50px",
        },
        {
          name: "countAquired",
          label: _("Max. Users"),
          width: "93px",
        },
        {
          name: "countAssigned",
          label: _("Assigned"),
          width: "93px",
        },
        {
          name: "countExpired",
          label: _("Expired"),
          width: "93px",
        },
        {
          name: "countAvailable",
          label: _("Available"),
          width: "93px",
        },
        {
          name: "latestDeliveryDate",
          label: _("Delivery"),
          width: "153px",
          formatter: function (value, object) {
            if (value) {
              value = dateLocale.format(new Date(value), {
                fullYear: true,
                selector: "date",
              });
            }
            return value;
          },
        },
      ];
      const columnsGroup = [
        {
          name: "productId",
          label: _("Medium ID"),
          formatter: function (value) {
            if (value && value.startsWith("urn:bilo:medium:")) {
              value = value.slice(16, value.length);
            }
            return value;
          },
        },
        {
          name: "title",
          label: _("Medium"),
          width: "200px",
        },
        {
          name: "publisher",
          label: _("Publisher"),
        },
        {
          name: "countLicenses",
          label: _("Acquired"),
          width: "adjust",
        },
        {
          name: "countLicensesAssigned",
          label: _("Assigned"),
          width: "adjust",
        },
        {
          name: "countLicensesExpired",
          label: _("Expired"),
          width: "adjust",
        },
        {
          name: "countLicensesAvailable",
          label: _("Available"),
          width: "adjust",
        },
        {
          name: "latestDeliveryDate",
          label: _("Delivery"),
          formatter: function (value, object) {
            if (value) {
              value = dateLocale.format(new Date(value), {
                fullYear: true,
                selector: "date",
              });
            }
            return value;
          },
        },
      ];
      // const columnsFooter = [
      //   {
      //     name: "sum",
      //     label: _("Sum"),
      //     width: "465px",
      //     sortable: false,
      //   },
      //   {
      //     name: "maxUser",
      //     label: this.maxUserSum, // TODO: fill real value
      //     width: "93px",
      //     sortable: false,
      //   },
      //   {
      //     name: "assigned",
      //     label: this.assignedSum, // TODO: fill real value
      //     width: "93px",
      //     sortable: false,
      //   },
      //   {
      //     name: "expired",
      //     label: this.expiredSum, // TODO: fill real value
      //     width: "93px",
      //     sortable: false,
      //   },
      //   {
      //     name: "available",
      //     label: this.availableSum, // TODO: fill real value
      //     width: "270px",
      //     sortable: false,
      //   },
      // ];

      this._grid = new Grid({
        actions: actions,
        columns: columns,
        moduleStore: store("productId", "licenses/products"),
        sortIndex: -8,
        addTitleOnCellHoverIfOverflow: true,
      });
      this._gridGroup = new Grid({
        actions: actions,
        columns: columnsGroup,
        moduleStore: store("productId", "licenses/products"),
        sortIndex: -8,
        addTitleOnCellHoverIfOverflow: true,
        gridOptions: {
          selectionMode: "single",
        },
        selectorType: "radio",
      });

      // FIXME(?) usage of private inherited variables
      aspect.around(
        this._grid._grid,
        "renderRow",
        lang.hitch(this, function (renderRow) {
          return lang.hitch(this, function (item, options) {
            const rowNode = renderRow.call(this._grid._grid, item, options);
            if (item.cover) {
              // .field-title should always exist. just to be safe
              const tooltipTarget =
                query(".field-title", rowNode)[0] || rowNode;
              on(rowNode, mouse.enter, function () {
                Tooltip.show(_("Loading cover..."), tooltipTarget);
                let showImage = true;
                const img = put(
                  document.body,
                  `img.dijitOffScreen.licensesCover[src="${item.cover}"]`
                );
                on(img, "load", function () {
                  if (showImage) {
                    const innerHTML = `<img src="${item.cover}" style="width: ${img.clientWidth}px; height: ${img.clientHeight}px">`;
                    Tooltip.show(innerHTML, tooltipTarget);
                  }
                });
                on(img, "error", function () {
                  if (showImage) {
                    Tooltip.show(_("Cover not found"), tooltipTarget);
                  }
                });
                on.once(rowNode, mouse.leave, function () {
                  showImage = false;
                  Tooltip.hide(tooltipTarget);
                });
              });
            }
            return rowNode;
          });
        })
      );

      // FIXME(?) usage of private inherited variables
      aspect.around(
        this._gridGroup,
        "renderRow",
        lang.hitch(this, function (renderRow) {
          return lang.hitch(this, function (item, options) {
            const rowNode = renderRow.call(this._gridGroup, item, options);
            if (item.cover) {
              // .field-title should always exist. just to be safe
              const tooltipTarget =
                query(".field-title", rowNode)[0] || rowNode;
              on(rowNode, mouse.enter, function () {
                Tooltip.show(_("Loading cover..."), tooltipTarget);
                let showImage = true;
                const img = put(
                  document.body,
                  `img.dijitOffScreen.licensesCover[src="${item.cover}"]`
                );
                on(img, "load", function () {
                  if (showImage) {
                    const innerHTML = `<img src="${item.cover}" style="width: ${img.clientWidth}px; height: ${img.clientHeight}px">`;
                    Tooltip.show(innerHTML, tooltipTarget);
                  }
                });
                on(img, "error", function () {
                  if (showImage) {
                    Tooltip.show(_("Cover not found"), tooltipTarget);
                  }
                });
                on.once(rowNode, mouse.leave, function () {
                  showImage = false;
                  Tooltip.hide(tooltipTarget);
                });
              });
            }
            return rowNode;
          });
        })
      );

      this.addChild(this._assignmentText);
      this.addChild(this._searchForm);
      if (this.moduleFlavor !== "licenses/allocation") {
        this.addChild(this._grid);
      }
    },
  });
});
