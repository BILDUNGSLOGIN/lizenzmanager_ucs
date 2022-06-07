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
  "dojo/dom-class",
  "dojo/Deferred",
  "dojox/html/entities",
  "umc/widgets/ComboBox",
  "umc/widgets/Form",
  "umc/widgets/Page",
  "umc/widgets/Text",
  "umc/i18n!umc/modules/licenses",
], function (
  declare,
  lang,
  domClass,
  Deferred,
  entities,
  ComboBox,
  Form,
  Page,
  Text,
  _
) {
  return declare("umc.modules.licenses.ChooseSchoolPage", [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    _form: null,

    _trySelectSchoolDeferred: null,
    trySelectSchool: function (schoolId) {
      this._trySelectSchoolDeferred = new Deferred();
      this._formReadyDeferred.then(
        lang.hitch(this, function () {
          this._form.setFormValues({
            school: schoolId,
          });
          this._form.submit();
        })
      );
      return this._trySelectSchoolDeferred;
    },

    onSchoolChosen: function (school) {
      // event stub
    },

    //// lifecycle
    buildRendering: function () {
      this.inherited(arguments);

      this._form = new Form({
        name: 'schoolForm',
        widgets: [
          {
            type: Text,
            size: "One",
            name: "headerText",
            content:
              "<h2>" + entities.encode(_("Please select a school")) + "</h2>",
          },
          {
            type: ComboBox,
            name: "school",
            label: _("School"),
            size: "OneThirds",
            dynamicValues: "licenses/schools",
          },
        ],
        buttons: [
          {
            name: "submit",
            label: _("Next"),
          },
        ],
        layout: [["headerText"], ["school", "submit"]],
        class: "dijitDisplayNone",
      });
      this._form.on(
        "submit",
        lang.hitch(this, function () {
          const schools = this._form.getWidget("school").getAllItems();
          const hasMultipleSchools = schools.length > 1;

          const schoolId = this._form.get("value").school;
          const school = schools.find(function (school) {
            return school.id === schoolId;
          });

          if (school) {
            this.onSchoolChosen(school, hasMultipleSchools);
            if (this._trySelectSchoolDeferred) {
              this._trySelectSchoolDeferred.resolve();
            }
          } else {
            // TODO do we want to reset the ComboBox for 'school' here?
            // If the set('value', val) is invalid it shows that with
            // an red exclamation mark but the text in the ComboBox is
            // still a valid school in the dropdown since we tried to set
            // the id of the entry directly and did not adjust the inputted text
            if (this._trySelectSchoolDeferred) {
              this._trySelectSchoolDeferred.cancel();
            }
          }
        })
      );
      this._formReadyDeferred = this._form.ready();
      this._formReadyDeferred.then(
        lang.hitch(this, function () {
          domClass.remove(this._form.domNode, "dijitDisplayNone");
          if (!this._trySelectSchoolDeferred) {
            const schools = this._form.getWidget("school").getAllItems();
            const hasMultipleSchools = schools.length > 1;
            if (!hasMultipleSchools && schools[0]) {
              this.onSchoolChosen(schools[0], hasMultipleSchools);
            }
          }
        })
      );

      this.addChild(this._form);
      this.standbyDuring(this._formReadyDeferred);
    },
  });
});
