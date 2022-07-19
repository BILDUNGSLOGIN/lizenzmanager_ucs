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
  "dojo/on",
  "dojo/date/locale",
  "dojox/html/entities",
  "dijit/Tooltip",
  "umc/dialog",
  "umc/store",
  "umc/tools",
  "umc/widgets/Page",
  "umc/widgets/Grid",
  "umc/widgets/CheckBox",
  "umc/widgets/DateBox",
  "umc/widgets/ComboBox",
  "umc/widgets/SearchForm",
  "umc/widgets/Text",
  "umc/widgets/TextBox",
  "umc/widgets/SuggestionBox",
  "umc/i18n!umc/modules/licenses",
], function (
  declare,
  lang,
  dom,
  domClass,
  on,
  dateLocale,
  entities,
  Tooltip,
  dialog,
  store,
  tools,
  Page,
  Grid,
  CheckBox,
  DateBox,
  ComboBox,
  SearchForm,
  Text,
  TextBox,
  SuggestionBox,
  _
) {
  return declare("umc.modules.licenses.LicenseSearchPage", [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    schoolId: null, // required parameter
    moduleFlavor: null, // required parameter
    showChangeSchoolButton: false,
    allocation: "",

    _licenseTypes: [],
    // reference to the currently active grid
    _grid: null,
    _gridFooter: null,
    _gridOverview: null,
    _gridAllocation: null,
    _gridGroup: null,
    _searchForm: null,

    _isAdvancedSearch: false,

    maxUserSum: "-",
    assignedSum: "-",
    expiredSum: "-",
    availableSum: "-",

    _toggleSearch: function () {
      this._isAdvancedSearch = !this._isAdvancedSearch;
      // toggle visibility
      console.log("Search", this)
      if (
        this.moduleFlavor === "licenses/licenses" ||
        this.allocation.usernames
      ) {
        [
          "timeFrom",
          "timeTo",
          "onlyAvailableLicenses",
          "publisher",
          "licenseType",
          "userPattern",
          "productId",
          "product",
          "licenseCode",
          "workgroup",
          "class"
        ].forEach(
          lang.hitch(this, function (widgetName) {
            const widget = this._searchForm.getWidget(widgetName);
            if (widget) {
              widget.set("visible", this._isAdvancedSearch);
            }
          })
        );
      } else {
        [
          "timeFrom",
          "timeTo",
          "onlyAvailableLicenses",
          "publisher",
          "userPattern",
          "productId",
          "product",
          "licenseCode",
          "workgroup",
          "class"
        ].forEach(
          lang.hitch(this, function (widgetName) {
            const widget = this._searchForm.getWidget(widgetName);
            if (widget) {
              widget.set("visible", this._isAdvancedSearch);
            }
          })
        );
      }

      this._searchForm
        .getWidget("pattern")
        .set("visible", !this._isAdvancedSearch);

      // update toggle button
      const button = this._searchForm.getButton("toggleSearch");
      if (this._isAdvancedSearch) {
        button.set("iconClass", "umcDoubleLeftIcon");
      } else {
        button.set("iconClass", "umcDoubleRightIcon");
      }
    },

    allocation: null,
    _setAllocationAttr: function (allocation) {
      this._set("allocation", allocation);
      domClass.remove(this._assignmentText.domNode, "dijitDisplayNone");
      if (allocation.usernames) {
        this._headerButtons.close?.set("visible", false);
        const count = allocation.usernames.length;
        const id = this.id + "-tooltip";
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
					${entities.encode(_("Choose the licenses you want to assign."))}
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
      } else if (allocation.school) {
        this._headerButtons.changeMedium?.set("visible", false);
        this._headerButtons.changeUsers?.set("visible", false);
        this._headerButtons.close?.set("visible", true);
        this.removeChild(this._gridAllocation);
        this.addChild(this._gridGroup);
        this._grid = this._gridGroup;
        const id = this.id + "-tooltip";
        const msg = `
				<p>
					${entities.encode(_("Assign licenses to selected school."))}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_("show selected school"))})
					</span>
				</p>
				<p>
					${entities.encode(_("Choose the licenses you want to assign."))}
				</p>
			`.trim();
        this._assignmentText.set("content", msg);
        const node = dom.byId(id);
        on(
          node,
          "click",
          lang.hitch(this, function (evt) {
            let label = `<div>${entities.encode(this.allocation.school)}</div>`;

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
        this._headerButtons.changeMedium?.set("visible", true);
        this._headerButtons.close?.set("visible", false);
        this.removeChild(this._gridAllocation);
        this.addChild(this._gridGroup);
        this._grid = this._gridGroup;
        const id = this.id + "-tooltip";
        let assignmentLabel = entities.encode(_("Assign licenses to selected workgroup/class."))
        if(allocation.userCount){
          assignmentLabel = entities.encode(
            allocation.userCount === 1
              ? _("Assign licenses to 1 selected user.")
              : _("Assign licenses to %s selected users.", allocation.userCount)
          )
        }
        const msg = `
				<p>
					${assignmentLabel}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_("show selected workgroup/class"))})
					</span>
				</p>
				<p>
					${entities.encode(_("Choose the licenses you want to assign."))}
				</p>
			`.trim();
        this._assignmentText.set("content", msg);
        const node = dom.byId(id);
        on(
          node,
          "click",
          lang.hitch(this, function (evt) {
            let label = "";
            if (allocation.workgroup && allocation.workgroup !== "") {
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

    query: function () {
      this.standbyDuring(
        // Deactivated in this flavor due to Issue #97
        this._searchForm.ready().then(
          lang.hitch(this, function () {
            if (this.moduleFlavor !== "licenses/licenses") {
              this._searchForm.submit();
            }
          })
        )
      );
    },

    onShowLicense: function (licenseCode) {
      // event stub
    },

    onChangeUsers: function () {
      this.resetAdvancedSearch();
    },

    onChangeProduct: function () {
      this.resetAdvancedSearch();
    },

    onBack: function () {
      // event stub
    },

    resetAdvancedSearch: function () {
      if (this._isAdvancedSearch) {
        this._toggleSearch();
      }
    },

    refreshGrid: function (values) {
      values.isAdvancedSearch = this._isAdvancedSearch;
      values.school = this.schoolId;
      if (this.moduleFlavor === "licenses/allocation") {
        values.isAdvancedSearch = true;
        values.onlyAvailableLicenses = true;
        if (this.allocation.usernames) {
          values.allocationProductId = this.allocation.productId;
          if (values.licenseType === "") {
            values.licenseType = ["SINGLE", "VOLUME"];
          } else if (values.licenseType == "SINGLE") {
            values.licenseType = ["SINGLE"];
          } else if (values.licenseType == "VOLUME") {
            values.licenseType = ["VOLUME"];
          }
        } else if (this.allocation.school) {
          values.licenseType = ["SCHOOL"];
        } else if (this.allocation.schoolClass || this.allocation.workgroup) {
          values.allocationProductId = this.allocation.productId;
          values.licenseType = ["WORKGROUP"];
        }
      } else {
        if (values.licenseType == "") {
          values.licenseType = [];
        } else if (values.licenseType == "SINGLE") {
          values.licenseType = ["SINGLE"];
        } else if (values.licenseType == "VOLUME") {
          values.licenseType = ["VOLUME"];
        } else if (values.licenseType == "SCHOOL") {
          values.licenseType = ["SCHOOL"];
        } else if (values.licenseType == "WORKGROUP") {
          values.licenseType = ["WORKGROUP"];
        }
      }
      this._grid.filter(values);
      values.licenseType = "";
    },

    // allow only either class or workgroup to be set
    onChooseDifferentClass: function () {
      const workgroupWidget = this._searchForm.getWidget("workgroup");
      workgroupWidget.setValue("")
    },
    onChooseDifferentWorkgroup: function () {
      const classWidget = this._searchForm.getWidget("class");
      classWidget.setValue("")
    },

    //// lifecycle
    postMixInProperties: function () {
      this.inherited(arguments);
      const headerButtons = [];
      if (this.moduleFlavor === "licenses/allocation") {
        this._licenseTypes = [
          {id: "", label: ""},
          {id: "SINGLE", label: _("Single license")},
          {id: "VOLUME", label: _("Volume license")},
        ];
        headerButtons.push({
          name: "changeUsers",
          label: _("Change user selection"),
          callback: lang.hitch(this, "onChangeUsers"),
        });
        headerButtons.push({
          name: "changeMedium",
          label: _("Change medium"),
          callback: lang.hitch(this, "onChangeProduct"),
        });
      } else {
        this._licenseTypes = [
          {id: "", label: ""},
          {id: "SINGLE", label: _("Single license")},
          {id: "VOLUME", label: _("Volume license")},
          {
            id: "WORKGROUP",
            label: _("Workgroup license"),
          },
          {
            id: "SCHOOL",
            label: _("School license"),
          },
        ];
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
          type: DateBox,
          name: "timeFrom",
          visible: false,
          label: _("Start import period"),
          size: "TwoThirds",
        },
        {
          type: DateBox,
          name: "timeTo",
          label: _("End import period"),
          size: "TwoThirds",
          visible: false,
        },
        {
          type: ComboBox,
          name: "licenseType",
          label: _("License type"),
          staticValues: this._licenseTypes,
          size: "TwoThirds",
          visible: false,
        },
        {
          type: TextBox,
          name: "userPattern",
          label: _("User ID"),
          description: _(
            "Search for licenses that have this user assigned. (Searches for 'first name', 'last name' and 'username')"
          ),
          size: "TwoThirds",
          visible: false,
        },
        {
          type: TextBox,
          name: "licenseCode",
          label: _("License code"),
          size: "TwoThirds",
          visible: false,
        },
        {
          type: TextBox,
          name: "pattern",
          label: "&nbsp;",
          inlineLabel: _("Search licenses"),
        },
      ];
      if (this.moduleFlavor !== "licenses/allocation") {
        console.log('allocation widgets')
        widgets.push(
          {
            type: TextBox,
            name: "product",
            label: _("Media Title"),
            size: "TwoThirds",
            visible: false,
          },
          {
            type: TextBox,
            name: "productId",
            label: _("Medium ID"),
            size: "TwoThirds",
            visible: false,
            formatter: function (value) {
              if (value && value.startsWith("urn:bilo:medium:")) {
                value = value.slice(16, value.length);
              }
              return value;
            },
          },
          {
            type: CheckBox,
            name: "onlyAvailableLicenses",
            label: _("Only assignable licenses"),
            value: false,
            size: "TwoThirds",
            visible: false,
          },
          {
            type: ComboBox,
            name: "publisher",
            label: _("Publisher"),
            staticValues: [{id: "", label: ""}],
            dynamicValues: "licenses/publishers",
            size: "TwoThirds",
            visible: false,
          },
          {
            type: ComboBox,
            name: "workgroup",
            label: _("Assigned to Workgroup"),
            staticValues: [{id: "", label: ""}],
            dynamicValues: "licenses/workgroups",
            dynamicOptions: {
              school: this.schoolId,
            },
            size: "TwoThirds",
            visible: false,
            onChange: lang.hitch(this, function (values) {
              this.onChooseDifferentWorkgroup(values);
            })
          },
          {
            type: SuggestionBox,
            name: "class",
            label: _("Assigned to Class"),
            staticValues: [{id: "", label: ""}],
            dynamicValues: "licenses/classes",
            dynamicOptions: {
              school: this.schoolId,
            },
            size: "TwoThirds",
            visible: false,
            onChange: lang.hitch(this, function (values) {
              this.onChooseDifferentClass(values);
            })
          },
        );
      }
      let layout = null;
      if (this.moduleFlavor === "licenses/allocation") {
        layout = [
          ["timeFrom", "timeTo", "userPattern"],
          [
            "licenseType",
            "licenseCode",
            "pattern",
            "submit",
            "toggleSearchLabel",
            "toggleSearch",
          ],
        ];
      } else {
        layout = [
          ["timeFrom", "timeTo", "onlyAvailableLicenses"],
          ["publisher", "licenseType", "userPattern"],
          ["workgroup", "class"],
          [
            "productId",
            "product",
            "licenseCode",
            "pattern",
            "submit",
            "toggleSearchLabel",
            "toggleSearch",
          ],
        ];
      }
      const buttons = [
        {
          name: "toggleSearch",
          labelConf: {
            class: "umcFilters",
          },
          label: _("Filters"),
          iconClass: "umcDoubleRightIcon",

          callback: lang.hitch(this, function () {
            this._toggleSearch();
          }),
        },
      ];
      this._searchForm = new SearchForm({
        class: "umcUDMSearchForm umcUDMSearchFormSimpleTextBox",
        region: "nav",
        widgets: widgets,
        buttons: buttons,
        layout: layout,
        onSearch: lang.hitch(this, function (values) {
          this.refreshGrid(values);
        }),
      });
      domClass.add(
        this._searchForm.getWidget("licenseCode").$refLabel$.domNode,
        "umcSearchFormElementBeforeSubmitButton"
      );

      const actions = [];
      if (this.moduleFlavor === "licenses/allocation") {
        actions.push({
          name: "assign",
          label: _("Assign licenses"),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: true,
          callback: lang.hitch(this, function (_idxs, licenses) {
            if (this.allocation.usernames) {
              tools
                .umcpCommand("licenses/assign_to_users", {
                  licenseCodes: licenses.map((license) => license.licenseCode),
                  usernames: this.allocation.usernames,
                })
                .then(
                  lang.hitch(this, function (response) {
                    const result = response.result;
                    let msg = "";
                    if (result.notEnoughLicenses) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "The number of selected licenses is not sufficient to assign a license to all selected users. Therefore, no licenses have been assigned. Please reduce the number of selected users or select more licenses and repeat the process."
                          )
                        ) +
                        "</p>";
                      dialog.alert(msg, _("Assigning licenses failed"));
                      return;
                    }
                    if (result.countSuccessfulAssignments) {
                      if (
                        result.countSuccessfulAssignments ===
                        this.allocation.usernames.length
                      ) {
                        msg +=
                          "<p>" +
                          entities.encode(
                            _(
                              "Licenses were successfully assigned to all %s selected users.",
                              result.countSuccessfulAssignments
                            )
                          ) +
                          "</p>";
                      } else {
                        msg +=
                          "<p>" +
                          entities.encode(
                            _(
                              "Licenses were successfully assigned to %s of the %s selected users.",
                              result.countSuccessfulAssignments,
                              this.allocation.usernames.length
                            )
                          ) +
                          "</p>";
                      }
                    }
                    if (result.failedAssignments.length) {
                      msg += "<p>";
                      msg +=
                        result.countSuccessfulAssignments > 0
                          ? entities.encode(
                            _(
                              "Some selected users could not be assigned licenses:"
                            )
                          )
                          : entities.encode(
                            _(
                              "Failed to assign licenses to the selected users:"
                            )
                          );
                      msg += "<ul>";
                      for (const error of result.failedAssignments) {
                        msg += "<li>" + entities.encode(error) + "</li>";
                      }
                      msg += "</ul>";
                      msg += "</p>";
                    }
                    if (result.validityInFuture.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _(
                          "Warning: The validity for the following assigned licenses lies in the future:"
                        )
                      );
                      msg += "<ul>";
                      for (const licenseCode of result.validityInFuture) {
                        msg += "<li>" + entities.encode(licenseCode) + "</li>";
                      }
                      msg += "</ul>";
                      msg += "</p>";
                    }
                    const title = _("Assigning licenses");
                    dialog.alert(msg, title);
                  })
                );
            } else if (this.allocation.school) {
              tools
                .umcpCommand("licenses/assign_to_school", {
                  licenseCodes: licenses.map((license) => license.licenseCode),
                  school: this.allocation.school,
                })
                .then(
                  lang.hitch(this, function (response) {
                    const result = response.result;
                    let msg = "";
                    if (result.notEnoughLicenses) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "The number of selected licenses is not sufficient to assign a license to the selected school."
                          )
                        ) +
                        "</p>";
                      dialog.alert(msg, _("Assigning licenses failed"));
                      return;
                    }
                    if (result.countSuccessfulAssignments) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "Licenses were successfully assigned to selected school.",
                            result.countSuccessfulAssignments
                          )
                        ) +
                        "</p>";
                    }
                    if (result.failedAssignments.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _("Failed to assign licenses to the selected school.")
                      );
                      for (const error of result.failedAssignments) {
                        msg += "<li>" + entities.encode(error) + "</li>";
                      }
                      msg += "</p>";
                    }
                    if (result.validityInFuture.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _(
                          "Warning: The validity for the following assigned licenses lies in the future:"
                        )
                      );
                      msg += "<ul>";
                      for (const licenseCode of result.validityInFuture) {
                        msg += "<li>" + entities.encode(licenseCode) + "</li>";
                      }
                      msg += "</ul>";
                      msg += "</p>";
                    }

                    const title = _("Assigning licenses");
                    dialog.alert(msg, title);
                  })
                );
            } else if (this.allocation.schoolClass) {
              tools
                .umcpCommand("licenses/assign_to_class", {
                  licenseCodes: licenses.map((license) => license.licenseCode),
                  schoolClass: this.allocation.schoolClass.substr(
                    3,
                    this.allocation.schoolClass.indexOf(",") - 3
                  ),
                })
                .then(
                  lang.hitch(this, function (response) {
                    const result = response.result;
                    let msg = "";
                    if (result.notEnoughLicenses) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "The number of selected licenses is not sufficient to assign a license to the selected class."
                          )
                        ) +
                        "</p>";
                      dialog.alert(msg, _("Assigning licenses failed"));
                      return;
                    }
                    if (result.countSuccessfulAssignments) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "Licenses were successfully assigned to selected class.",
                            result.countSuccessfulAssignments
                          )
                        ) +
                        "</p>";
                    }
                    if (result.failedAssignments.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _("Failed to assign licenses to the selected class.")
                      );
                      for (const error of result.failedAssignments) {
                        msg += "<li>" + entities.encode(error) + "</li>";
                      }
                      msg += "</p>";
                    }
                    if (result.validityInFuture.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _(
                          "Warning: The validity for the following assigned licenses lies in the future:"
                        )
                      );
                      msg += "<ul>";
                      for (const licenseCode of result.validityInFuture) {
                        msg += "<li>" + entities.encode(licenseCode) + "</li>";
                      }
                      msg += "</ul>";
                      msg += "</p>";
                    }

                    const title = _("Assigning licenses");
                    dialog.alert(msg, title);
                  })
                );
            } else if (this.allocation.workgroup) {
              tools
                .umcpCommand("licenses/assign_to_workgroup", {
                  licenseCodes: licenses.map((license) => license.licenseCode),
                  workgroup: this.allocation.workgroup.substr(
                    3,
                    this.allocation.workgroup.indexOf(",") - 3
                  ),
                })
                .then(
                  lang.hitch(this, function (response) {
                    const result = response.result;
                    let msg = "";
                    if (result.notEnoughLicenses) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "The number of selected licenses is not sufficient to assign a license to the selected workgroup."
                          )
                        ) +
                        "</p>";
                      dialog.alert(msg, _("Assigning licenses failed"));
                      return;
                    }
                    if (result.countSuccessfulAssignments) {
                      msg +=
                        "<p>" +
                        entities.encode(
                          _(
                            "Licenses were successfully assigned to selected workgroup.",
                            result.countSuccessfulAssignments
                          )
                        ) +
                        "</p>";
                    }
                    if (result.failedAssignments.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _(
                          "Failed to assign licenses to the selected workgroup."
                        )
                      );
                      for (const error of result.failedAssignments) {
                        msg += "<li>" + entities.encode(error) + "</li>";
                      }
                      msg += "</p>";
                    }
                    if (result.validityInFuture.length) {
                      msg += "<p>";
                      msg += entities.encode(
                        _(
                          "Warning: The validity for the following assigned licenses lies in the future:"
                        )
                      );
                      msg += "<ul>";
                      for (const licenseCode of result.validityInFuture) {
                        msg += "<li>" + entities.encode(licenseCode) + "</li>";
                      }
                      msg += "</ul>";
                      msg += "</p>";
                    }

                    const title = _("Assigning licenses");
                    dialog.alert(msg, title);
                  })
                );
            }
          }),
        });
      } else {
        actions.push({
          name: "edit",
          label: _("Edit"),
          iconClass: "umcIconEdit",
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: false,
          callback: lang.hitch(this, function (_idxs, licenses) {
            this.onShowLicense(licenses[0].licenseCode);
          }),
        });
      }

      const columns = [
        {
          name: "licenseCode",
          label: _("License code"),
          width: "60px",
        },
        {
          name: "productId",
          label: _("Medium ID"),
          width: "60px",
          formatter: function (value) {
            if (value && value.startsWith("urn:bilo:medium:")) {
              value = value.slice(16, value.length);
            }
            return value;
          },
        },
        {
          name: "productName",
          label: _("Medium"),
          width: "200px",
        },
        {
          name: "publisher",
          label: _("Publisher"),
          width: "50px",
        },
        {
          name: "licenseTypeLabel",
          label: _("License type"),
        },
        {
          name: "countAquired",
          label: _("Max. Users"),
          width: "adjust",
        },
        {
          name: "countAssigned",
          label: _("Assigned"),
          width: "adjust",
        },
        {
          name: "countExpired",
          label: _("Expired"),
          width: "adjust",
        },
        {
          name: "countAvailable",
          label: _("Available"),
          width: "adjust",
        },
        {
          name: "importDate",
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
      const columnsOverview = [
        {
          name: "licenseCode",
          label: _("License code"),
          width: "66px",
        },
        {
          name: "productId",
          label: _("Medium ID"),
          width: "66px",
          formatter: function (value) {
            if (value && value.startsWith("urn:bilo:medium:")) {
              value = value.slice(16, value.length);
            }
            return value;
          },
        },
        {
          name: "productName",
          label: _("Medium"),
          width: "200px",
        },
        {
          name: "publisher",
          label: _("Publisher"),
          width: "50px",
        },
        {
          name: "licenseTypeLabel",
          label: _("License type"),
          width: "66px",
        },
        {
          name: "for",
          label: _("For"),
          width: "66px",
        },
        {
          name: "countAquired",
          label: _("Max. Users"),
          width: "66px",
        },
        {
          name: "countAssigned",
          label: _("Assigned"),
          width: "66px",
        },
        {
          name: "countExpired",
          label: _("Expired"),
          width: "66px",
        },
        {
          name: "countAvailable",
          label: _("Available"),
          width: "66px",
        },
        {
          name: "importDate",
          label: _("Delivery"),
          width: "66px",
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
      // {
      //   name: "sum",
      //   label: _("Sum"),
      //   width: "370px",
      //   sortable: false,
      // },
      //   {
      //     name: "maxUser",
      //     label: this.maxUserSum, // TODO: fill real value
      //     width: "66px",
      //     sortable: false,
      //   },
      //   {
      //     name: "assigned",
      //     label: this.assignedSum, // TODO: fill real value
      //     width: "66px",
      //     sortable: false,
      //   },
      //   {
      //     name: "expired",
      //     label: this.expiredSum, // TODO: fill real value
      //     width: "66px",
      //     sortable: false,
      //   },
      //   {
      //     name: "available",
      //     label: this.availableSum, // TODO: fill real value
      //     width: "122px",
      //     sortable: false,
      //   },
      // ];

      const columnsGroup = [
        {
          name: "licenseCode",
          label: _("License code"),
        },
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
          name: "productName",
          label: _("Medium"),
          width: "200px",
        },
        {
          name: "publisher",
          label: _("Publisher"),
          width: "50px",
        },
        {
          name: "licenseTypeLabel",
          label: _("License type"),
        },
        {
          name: "for",
          label: _("For"),
        },
        {
          name: "countAquired",
          label: _("Max. Users"),
          width: "adjust",
        },
        {
          name: "validityStart",
          label: _("Validity start"),
          visible: false,
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
        {
          name: "validityEnd",
          label: _("Validity end"),
          visible: false,
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
        {
          name: "importDate",
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

      this._gridAllocation = new Grid({
        actions: actions,
        columns: columns,
        moduleStore: store("licenseCode", "licenses"),
        sortIndex: -10,
        addTitleOnCellHoverIfOverflow: true,
      });

      // this._gridFooter = new Grid({
      //   columns: columnsFooter,
      //   class: "licensesTable__sum",
      //   moduleStore: store("licenseCode", "licenses"),
      // });

      this._gridOverview = new Grid({
        actions: actions,
        columns: columnsOverview,
        moduleStore: store("licenseCode", "licenses"),
        sortIndex: -10,
        addTitleOnCellHoverIfOverflow: true,
        class: "licensesTable__licenses",
        gridOptions: {
          selectionMode: "single",
        },
        selectorType: "radio",
      });

      this._gridGroup = new Grid({
        actions: actions,
        columns: columnsGroup,
        moduleStore: store("licenseCode", "licenses"),
        sortIndex: -10,
        addTitleOnCellHoverIfOverflow: true,
        gridOptions: {
          selectionMode: "single",
        },
        selectorType: "radio",
      });

      this.addChild(this._assignmentText);
      this.addChild(this._searchForm);

      if (this.moduleFlavor == "licenses/allocation") {
        this.addChild(this._gridAllocation);
        this._grid = this._gridAllocation
      } else {
        this.addChild(this._gridOverview);
        this._grid = this._gridOverview
      }
    },
  });
});
