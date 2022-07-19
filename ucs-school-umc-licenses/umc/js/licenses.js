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
  "dojo/on",
  "dojox/html/entities",
  "umc/widgets/Module",
  "umc/widgets/Text",
  "./licenses/ChooseSchoolPage",
  "./licenses/LicenseDetailPage",
  "./licenses/LicenseSearchPage",
  "./licenses/ProductDetailPage",
  "./licenses/ProductSearchPage",
  "./licenses/UserSelectionPage",
  "./licenses/ImportMediaLicensePage",
  "umc/i18n!umc/modules/licenses",
  "xstyle/css!./licenses.css",
], function (
  declare,
  lang,
  on,
  entities,
  Module,
  Text,
  ChooseSchoolPage,
  LicenseDetailPage,
  LicenseSearchPage,
  ProductDetailPage,
  ProductSearchPage,
  UserSelectionPage,
  ImportMediaLicensePage,
  _
) {
  return declare("umc.modules.licenses", [Module], {
    //// overwrites
    selectablePagesToLayoutMapping: {
      _licenseDetailPage: "searchpage-grid",
      _licenseSearchPage: "searchpage-grid",
      _productDetailPage: "searchpage-grid",
      _productSearchPage: "searchpage-grid",
      _userSelectionPage: "searchpage-grid",
      _importMediaLicensePage: "searchpage-grid",
    },

    //// self
    _schoolId: "",
    _chooseSchoolPage: null,
    _licenseSearchPage: null,
    _licenseDetailPage: null,
    _userSelectionPage: null,
    _productSearchPage: null,
    _productDetailPage: null,
    _lastSelectedProductId: null,
    _importMediaLicensePage: null,

    _showLicense: function (licenseCode) {
      this._licenseDetailPage.load(licenseCode).then(
        lang.hitch(this, function (licenseCode) {
          this.set(
            "title",
            this.defaultTitle + ": " + entities.encode(licenseCode)
          );
          this.selectChild(this._licenseDetailPage);
        })
      );
    },
    _buildLicensesModule: function (schoolId, hasMultipleSchools) {
      if (this._licenseSearchPage) {
        this._licenseSearchPage.destroyRecursive();
      }
      if (this._licenseDetailPage) {
        this._licenseDetailPage.destroyRecursive();
      }

      this._licenseSearchPage = new LicenseSearchPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        showChangeSchoolButton: hasMultipleSchools,
        moduleFlavor: this.moduleFlavor,
      });
      on(
        this._licenseSearchPage,
        "chooseDifferentSchool",
        lang.hitch(this, function () {
          this._chooseDifferentSchool();
        })
      );
      on(
        this._licenseSearchPage,
        "showLicense",
        lang.hitch(this, function (licenseCode) {
          this._showLicense(licenseCode);
        })
      );

      this._licenseDetailPage = new LicenseDetailPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
      });
      on(
        this._licenseDetailPage,
        "back",
        lang.hitch(this, function () {
          this.resetTitle();
          this.selectChild(this._licenseSearchPage);
        })
      );

      this.addChild(this._licenseSearchPage);
      this.addChild(this._licenseDetailPage);

      this.selectChild(this._licenseSearchPage);
      this._licenseSearchPage.query();
    },

    _buildAssignmentModule: function (schoolId, hasMultipleSchools) {
      if (this._userSelectionPage) {
        this._userSelectionPage.destroyRecursive();
      }
      if (this._productSearchPage) {
        this._productSearchPage.destroyRecursive();
      }

      if (this._licenseSearchPage) {
        this._licenseSearchPage.destroyRecursive();
      }
      this._userSelectionPage = new UserSelectionPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        showChangeSchoolButton: hasMultipleSchools,
      });
      on(
        this._userSelectionPage,
        "chooseDifferentSchool",
        lang.hitch(this, function () {
          this._chooseDifferentSchool();
        })
      );
      on(
        this._userSelectionPage,
        "licenseTypeSelected",
        lang.hitch(this, function (licenseType) {
          switch (licenseType) {
            case "SCHOOL":
              this.set("title", _("Assign school licenses"));
              break;
            case "WORKGROUP":
              this.set("title", _("Assign group licenses"));
              break;
            default:
              this.set("title", _("Assign media licenses"));
          }
        })
      );
      on(
        this._userSelectionPage,
        "usersSelected",
        lang.hitch(this, function (usernames) {
          this._productSearchPage.set("allocation", {
            usernames: usernames,
          });
          this.selectChild(this._productSearchPage);
          this._productSearchPage.refreshGrid({ pattern: "" });
        })
      );
      on(
        this._userSelectionPage,
        "schoolSelected",
        lang.hitch(this, function (school) {
          this._licenseSearchPage.set("allocation", {
            school: school,
          });
          this.selectChild(this._licenseSearchPage);

          this._licenseSearchPage.refreshGrid({
            licenseCode: "",
            licenseType: "",
            pattern: "",
            timeFrom: null,
            timeTo: null,
            userPattern: "",
          });
        })
      );
      on(
        this._userSelectionPage,
        "workgroupSelected",
        lang.hitch(
          this,
          function (schoolClass, workgroup, className, workgroupName) {
            this._productSearchPage.set("allocation", {
              schoolClass: schoolClass,
              workgroup: workgroup,
              className: className,
              workgroupName: workgroupName,
            });
            this.selectChild(this._productSearchPage);
            this._productSearchPage.refreshGrid({ pattern: "" });
          }
        )
      );

      this._productSearchPage = new ProductSearchPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        moduleFlavor: this.moduleFlavor,
      });
      on(
        this._productSearchPage,
        "changeUsers",
        lang.hitch(this, function () {
          this.selectChild(this._userSelectionPage);
        })
      );
      on(
        this._productSearchPage,
        "productChosen",
        lang.hitch(this, function (productId, usernames) {
          this._licenseSearchPage.set("allocation", {
            productId: productId,
            usernames: usernames,
          });
          this.selectChild(this._licenseSearchPage);
          if (this._lastSelectedProductId !== productId) {
            this._licenseSearchPage.query();
          }
          this._lastSelectedProductId = productId;
          this._licenseSearchPage.refreshGrid({ pattern: "" });
        })
      );
      on(
        this._productSearchPage,
        "productChosenForWorkgroup",
        lang.hitch(
          this,
          function (
            productId,
            workgroup,
            schoolClass,
            workgroupName,
            className,
            userCount
          ) {
            this._licenseSearchPage.set("allocation", {
              productId: productId,
              workgroup: workgroup,
              schoolClass: schoolClass,
              className: className,
              workgroupName: workgroupName,
              userCount: userCount
            });
            this.selectChild(this._licenseSearchPage);
            if (this._lastSelectedProductId !== productId) {
              this._licenseSearchPage.query();
            }
            this._licenseSearchPage.refreshGrid({
              licenseCode: "",
              licenseType: "",
              pattern: "",
              timeFrom: null,
              timeTo: null,
              userPattern: "",
            });
            this._lastSelectedProductId = productId;
          }
        )
      );

      this._licenseSearchPage = new LicenseSearchPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        moduleFlavor: this.moduleFlavor,
      });
      on(
        this._licenseSearchPage,
        "changeUsers",
        lang.hitch(this, function () {
          this.selectChild(this._userSelectionPage);
        })
      );
      on(
        this._licenseSearchPage,
        "changeProduct",
        lang.hitch(this, function () {
          this.selectChild(this._productSearchPage);
        })
      );

      this.addChild(this._userSelectionPage);
      this.addChild(this._productSearchPage);
      this.addChild(this._licenseSearchPage);

      this.selectChild(this._userSelectionPage);
      this._userSelectionPage.query();
      // don't query until user selected
      //this._productSearchPage.query();
    },

    _showProduct: function (productId) {
      this._productDetailPage.load(productId).then(
        lang.hitch(this, function () {
          if (productId.startsWith("urn:bilo:medium:")) {
            productId = productId.slice(16, productId.length);
          }
          this.set(
            "title",
            this.defaultTitle + ": " + entities.encode(productId)
          );
          this.selectChild(this._productDetailPage);
        })
      );
    },
    _buildProductsModule: function (schoolId, hasMultipleSchools) {
      if (this._productSearchPage) {
        this._productSearchPage.destroyRecursive();
      }

      if (this._productDetailPage) {
        this._productDetailPage.destroyRecursive();
      }

      this._productSearchPage = new ProductSearchPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        showChangeSchoolButton: hasMultipleSchools,
        moduleFlavor: this.moduleFlavor,
      });
      on(
        this._productSearchPage,
        "chooseDifferentSchool",
        lang.hitch(this, function () {
          this._chooseDifferentSchool();
        })
      );
      on(
        this._productSearchPage,
        "showProduct",
        lang.hitch(this, function (productId) {
          this._showProduct(productId);
        })
      );

      this._productDetailPage = new ProductDetailPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
      });
      on(
        this._productDetailPage,
        "back",
        lang.hitch(this, function () {
          this.resetTitle();
          this.selectChild(this._productSearchPage);
        })
      );

      this.addChild(this._productSearchPage);
      this.addChild(this._productDetailPage);

      this.selectChild(this._productSearchPage);
      this._productSearchPage.query();
    },
    _buildImportModule: function (schoolId, hasMultipleSchools) {
      if (this._importMediaLicensePage) {
        this._importMediaLicensePage.destroyRecursive();
      }

      this._importMediaLicensePage = new ImportMediaLicensePage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
        schoolId: schoolId,
        showChangeSchoolButton: hasMultipleSchools,
        moduleFlavor: this.moduleFlavor,
      });
      on(
        this._importMediaLicensePage,
        "chooseDifferentSchool",
        lang.hitch(this, function () {
          this._chooseDifferentSchool();
        })
      );

      this.addChild(this._importMediaLicensePage);
      this.selectChild(this._importMediaLicensePage);
    },

    _schoolLabelWidget: null,
    schoolLabel: "&nbsp;",
    _setSchoolLabelAttr: function (schoolLabel) {
      if (!this._schoolLabelWidget) {
        this._schoolLabelWidget = new Text({
          content: "",
        });
        // FIXME(?) usage of private inherited variables
        this._top._left.addChild(this._schoolLabelWidget);
      }
      this._schoolLabelWidget.set("content", schoolLabel);
      this._set("schoolLabel", schoolLabel);
    },

    _trySelectSchool: function (schoolId) {
      this._chooseDifferentSchool();
      return this._chooseSchoolPage.trySelectSchool(schoolId);
    },

    _chooseDifferentSchool: function (tryToSelectThisSchool) {
      this._schoolId = null;
      this.set("schoolLabel", "&nbsp;");
      this.selectChild(this._chooseSchoolPage);
    },

    _updateModuleState: function () {
      this.set("moduleState", this.get("moduleState"));
    },

    _getModuleStateAttr: function () {
      const state = [];
      if (this._schoolId) {
        state.push("school");
        state.push(this._schoolId);
      }
      switch (this.moduleFlavor) {
        case "licenses/licenses":
          if (this._licenseDetailPage && this._licenseDetailPage.selected) {
            state.push("license");
            state.push(this._licenseDetailPage.license.licenseCode);
          }
          break;
        case "licenses/allocation":
          break;
        case "licenses/products":
          if (this._productDetailPage && this._productDetailPage.selected) {
            state.push("product");
            state.push(this._productDetailPage.product.productId);
          }
          break;
        case "licenses/import":
          break;
      }
      return state.join(":");
    },

    _setModuleStateAttr: function (state) {
      this._set("moduleState", state);
      if (state === this.get("moduleState")) {
        return;
      }

      const stateParts = state.split(":");
      const schoolKey = stateParts.shift();
      const schoolId = stateParts.shift();
      if (schoolKey === "school" && schoolId) {
        this._trySelectSchool(schoolId).then(
          lang.hitch(this, function () {
            const detailKey = stateParts.shift();
            if (
              detailKey === "license" &&
              this.moduleFlavor === "licenses/licenses"
            ) {
              const licenseCode = stateParts.join(":");
              if (licenseCode) {
                this._showLicense(licenseCode);
              }
            } else if (
              detailKey === "product" &&
              this.moduleFlavor === "licenses/products"
            ) {
              const productId = stateParts.join(":");
              if (productId) {
                this._showProduct(productId);
              }
            }
          })
        );
      }
    },

    //// lifecycle
    buildRendering: function () {
      this.inherited(arguments);

      this._chooseSchoolPage = new ChooseSchoolPage({
        standbyDuring: lang.hitch(this, "standbyDuring"),
      });
      on(
        this._chooseSchoolPage,
        "schoolChosen",
        lang.hitch(this, function (school, hasMultipleSchools) {
          this._schoolId = school.id;
          this.set(
            "schoolLabel",
            _("for %(school)s", {
              school: entities.encode(school.label),
            })
          );
          switch (this.moduleFlavor) {
            case "licenses/licenses":
              this._buildLicensesModule(school.id, hasMultipleSchools);
              break;
            case "licenses/allocation":
              this._buildAssignmentModule(school.id, hasMultipleSchools);
              break;
            case "licenses/products":
              this._buildProductsModule(school.id, hasMultipleSchools);
              break;
            case "licenses/import":
              this._buildImportModule(school.id, hasMultipleSchools);
              break;
          }
        })
      );

      this.watch("selectedChildWidget", lang.hitch(this, "_updateModuleState"));
      this.addChild(this._chooseSchoolPage);
    },
  });
});
