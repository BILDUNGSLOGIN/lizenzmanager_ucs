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
  "dojox/html/entities",
  "umc/store",
  "umc/widgets/ComboBox",
  "umc/widgets/Grid",
  "umc/widgets/Page",
  "umc/widgets/SearchBox",
  "umc/widgets/SearchForm",
  "umc/widgets/Form",
  "umc/widgets/SuggestionBox",
  "umc/widgets/Text",
  "umc/i18n!umc/modules/licenses",
], function (
  declare,
  lang,
  entities,
  store,
  ComboBox,
  Grid,
  Page,
  SearchBox,
  SearchForm,
  Form,
  SuggestionBox,
  Text,
  _
) {
  return declare("umc.modules.licenses.UserSelectionPage", [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    schoolId: null, // required parameter
    showChangeSchoolButton: false,

    selectedLicenseType: "",

    query: function () {
      this.standbyDuring(
        this._searchForm.ready().then(
          lang.hitch(this, function () {
            // this._searchForm.submit(); Deactivated due to Issue #85
          })
        )
      );
    },

    onBack: function () {
      // event stub
    },

    onChooseDifferentSchool: function () {
      // event stub
    },

    onUsersSelected: function (userIds) {},

    onSchoolSelected: function (schoolId) {},

    onLicenseTypeSelected: function (licenseType) {},

    onWorkgroupSelected: function (
      classId,
      workgroupId,
      className,
      workgroupName
    ) {},

    onSearchSubmit: function (values) {
      this.toogleNotification("");
      if (this.selectedLicenseType === "SINGLE_AND_VOLUME") {
        this._searchForm.getButton("submit").set("visible", false);
        this.addChild(this._grid);
        if (values.class.trim() === "") {
          const classWidget = this._searchForm.getWidget("class");
          classWidget.reset();
          values.class = classWidget.get("value");
        }
        values.school = this.schoolId;
        values.licenseType = this.selectedLicenseType;
        this._grid.filter(values);
      }
    },

    toogleNotification: function (message) {
      const notificationWidget = this._searchForm.getWidget("NotificationText");
      if (message) {
        notificationWidget.set("visible", true);
        notificationWidget.set(
          "content",
          "<p>" + entities.encode(_(message)) + "</p>"
        );
      } else {
        notificationWidget.set("visible", false);
        notificationWidget.set("content", "");
      }
    },

    onChooseDifferentWorkgroup: function (workingGroupId) {
      const classWidget = this._searchForm.getWidget("class");
      if (this.selectedLicenseType === "WORKGROUP")
        this.setButtonDisabled(
          this.isButtonDisabled(classWidget, workingGroupId)
        );

      //clear existing notification
      this.toogleNotification("");
      if (
        classWidget &&
        classWidget.value !== "__all__" &&
        workingGroupId !== "__all__"
      ) {
        classWidget.reset();
        this.toogleNotification(
          "You can either choose Class or Workgroup, Class has been reset."
        );
      }
    },

    onChooseDifferentClass: function (classId) {
      const workgroupWidget = this._searchForm.getWidget("workgroup");
      if (this.selectedLicenseType === "WORKGROUP")
        this.setButtonDisabled(this.isButtonDisabled(workgroupWidget, classId));

      //clear existing notification
      this.toogleNotification("");
      if (
        workgroupWidget &&
        workgroupWidget.value !== "__all__" &&
        classId !== "__all__"
      ) {
        workgroupWidget.reset();
        this.toogleNotification(
          "You can either choose Class or Workgroup, Workgroup has been reset."
        );
      }
    },

    onChooseLicenseType: function (licenseType) {
      this.toogleNotification("");
      this.removeChild(this._grid);
      this._searchForm.getButton("submit").set("visible", true);
      this.onLicenseTypeSelected(licenseType);
      switch (licenseType) {
        case "SCHOOL":
          this.selectedLicenseType = "SCHOOL";
          this._searchForm.getWidget("class").set("visible", false);
          this._searchForm.getWidget("workgroup").set("visible", false);
          this._searchForm.getWidget("pattern").set("visible", false);
          this.setButtonDisabled(false);
          break;
        case "WORKGROUP":
          this.selectedLicenseType = "WORKGROUP";
          this._searchForm.getWidget("pattern").set("visible", false);
          this._searchForm.getWidget("class").set("visible", true);
          this._searchForm.getWidget("workgroup").set("visible", true);
          let isButtonDisabled = this.isButtonDisabled(
            this._searchForm.getWidget("class"),
            this._searchForm.getWidget("workgroup")
          );
          this.setButtonDisabled(isButtonDisabled);
          break;
        default:
          this.selectedLicenseType = "SINGLE_AND_VOLUME";
          this._searchForm.getWidget("class").set("visible", true);
          this._searchForm.getWidget("workgroup").set("visible", true);
          this._searchForm.getWidget("pattern").set("visible", true);
          this.setButtonDisabled(false);
      }
    },

    onBackBtnClick: function () {
      this.toogleNotification("");
      this.removeChild(this._grid);
      const licenseTypeWidget = this._searchForm.getWidget("licenseType");
      licenseTypeWidget.reset();
      this._headerButtons.changeSchool.set("visible", true);
      this._headerButtons.back.set("visible", false);
      this.addChild(this._searchForm);
    },

    isButtonDisabled: function (schoolClass, workgroup) {
      isDisabled = false;
      if (schoolClass == "__all__" && workgroup == "__all__") {
        isDisabled = true;
      }
      return isDisabled;
    },

    setButtonDisabled: function (disable) {
      this._searchForm.getButton("submit").set("disabled", disable);
    },

    //// lifecycle
    postMixInProperties: function () {
      this.inherited(arguments);
      this.headerButtons = [
        {
          name: "changeSchool",
          label: _("Change school"),
          callback: lang.hitch(this, "onChooseDifferentSchool"),
          visible: false,
        },
        {
          name: "back",
          label: _("Back"),
          callback: lang.hitch(this, function () {
            this.onBackBtnClick();
          }),
          visible: false,
        },
      ];
    },

    buildRendering: function () {
      this.inherited(arguments);
      this.removeChild(this._grid);

      const notificationWidget = {
        type: Text,
        size: "One",
        name: "NotificationText",
        content: "",
        visible: false,
      };

      const workgroupWidget = {
        type: ComboBox,
        name: "workgroup",
        staticValues: [{ id: "__all__", label: _("All workgroups") }],
        dynamicValues: "licenses/workgroups",
        dynamicOptions: {
          school: this.schoolId,
        },
        label: _("Workgroup"),
        description: _(
          "Select a workgroup or enter free text (e.g. a part of a workgroup name)"
        ),
        size: "OneFourth",
        onChange: lang.hitch(this, function (values) {
          this.onChooseDifferentWorkgroup(values);
        }),
      };

      const classWidget = {
        type: SuggestionBox,
        name: "class",
        staticValues: [{ id: "__all__", label: _("All classes") }],
        dynamicValues: "licenses/classes",
        dynamicOptions: {
          school: this.schoolId,
        },
        label: _("Class"),
        description: _(
          "Select a class or enter free text (e.g. a part of a class name)"
        ),
        size: "OneFourth",
        onChange: lang.hitch(this, function (values) {
          this.onChooseDifferentClass(values);
        }),
      };

      const widgets = [
        {
          type: ComboBox,
          name: "licenseType",
          label: _("License type"),
          staticValues: [
            { id: "SINGLE_AND_VOLUME", label: _("Single- / Volumelicense") },
            {
              id: "WORKGROUP",
              label: _("Workgroup license"),
            },
            {
              id: "SCHOOL",
              label: _("School license"),
            },
          ],
          size: "OneFourth",
          onChange: lang.hitch(this, function (values) {
            this.onChooseLicenseType(values);
          }),
        },
        classWidget,
        workgroupWidget,
        notificationWidget,
        {
          type: SearchBox,
          name: "pattern",
          label: _("User"),
          inlineLabel: _("Search user"),
          size: "OneFourth",
          onSearch: lang.hitch(this, function () {
            this._searchForm.submit();
          }),
        },
      ];

      this._searchForm = new SearchForm({
        name: "searchForm",
        region: "nav",
        widgets: widgets,
        buttons: [
          {
            name: "submit",
            label: _("Next"),
            visible: true,
            disable: false,
          },
        ],
        layout: [
          ["licenseType", "class", "workgroup", "pattern", "submit"],
          ["NotificationText"],
        ],
        onSearch: lang.hitch(this, function (values) {
          switch (this.selectedLicenseType) {
            case "SCHOOL":
              this.onSchoolSelected(this.schoolId);
              break;
            case "WORKGROUP":
              let className =
                this._searchForm.getWidget("class").displayedValue;
              let workgroupName =
                this._searchForm.getWidget("workgroup").displayedValue;

              this.onWorkgroupSelected(
                values.class,
                values.workgroup,
                className,
                workgroupName
              );
              break;
            case "SINGLE_AND_VOLUME":
              this.onSearchSubmit(values);
          }
        }),
      });

      const actions = [
        {
          name: "allocate",
          label: _("Assign licenses"),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: true,
          callback: lang.hitch(this, function () {
            this.onUsersSelected(this._grid.getSelectedIDs());
          }),
        },
      ];
      const columns = [
        {
          name: "username",
          label: _("Username"),
        },
        {
          name: "lastname",
          label: _("Last name"),
        },
        {
          name: "firstname",
          label: _("First name"),
        },
        {
          name: "role",
          label: _("Role"),
        },
        {
          name: "class",
          label: _("Class"),
        },
        {
          name: "workgroup",
          label: _("Workgroup"),
        },
      ];
      this._grid = new Grid({
        actions: actions,
        columns: columns,
        moduleStore: store("username", "licenses/users"),
      });

      this.addChild(this._searchForm);
    },
  });
});
