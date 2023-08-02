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
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/store',
  'umc/widgets/ComboBox',
  'umc/widgets/Grid',
  '../../common/Page',
  'umc/widgets/SearchBox',
  'umc/widgets/SearchForm',
  'umc/widgets/Form',
  'umc/widgets/SuggestionBox',
  'umc/widgets/Text',
  'dijit/_WidgetBase',
  'dijit/_TemplatedMixin',
  'umc/i18n!umc/modules/licenses',
], function(
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
    _WidgetBase,
    _TemplatedMixin,
    _,
) {
  const _Description = declare('umc.modules.licenses.Description',
      [_WidgetBase, _TemplatedMixin], {
        //// overwrites
        templateString: `
<div class="description-columns">
    <div class="description-col">
    <h5>${_('Single and Volume Licences')}</h5>
    ${_('In the case of single licenses, each license has its own license code. This can only be assigned once in order to give a person authorization to use a medium.' +
            'In the case of volume licenses, multiple licenses are associated with one license code. I.e. the license code can be assigned several times (up to the specified maximum number) in order to grant usage rights for a medium to a corresponding number of persons. The assignment itself can also be divided into several cases.')}
    </div class="description-col">
    <div class="description-col">
    <h5>${_('Learning Group Licences')}</h5>
    ${_('By assigning a learning group license, all members of a class or learning group (up to the specified maximum number, if applicable) are granted usage rights via a license code. If a new member joins the class or learning group during the license term, he or she will automatically also gain the usage authority for the relevant medium. If a member leaves the class or learning group, he or she automatically loses the usage authorization.\n' +
            'A learning group license can only be assigned once and cannot be released again.')}
    </div class="description-col">
    <div class="description-col">
    <h5>${_('School Licences')}</h5>
    ${_('By assigning a school license, a license code is issued to all students and teaching staff of a school staff (up to the specified maximum number, if applicable). In the case of a special school license for teachers, the usage authorization applies only to the teaching staff. Anyone who joins the school during the term of the license is automatically also granted a right to use the relevant medium.\n' +
            'A school license can only be assigned once and cannot be released again.')}
    </div class="description-col">
</div>
		`,

        //// self
        standbyDuring: null, // required

      });

  return declare('umc.modules.licenses.UserSelectionPage', [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    getSchoolId: function() {}, // required parameter
    setUserIds: function() {}, // required parameter
    showChangeSchoolButton: false,

    selectedLicenseType: '',

    query: function() {
      this.standbyDuring(
          this._searchForm.ready().then(
              lang.hitch(this, function() {
                // this._searchForm.submit(); Deactivated due to Issue #85
              }),
          ),
      );
    },

    onSearchSubmit: function(values) {
      this.toogleNotification('');
      if (this.selectedLicenseType === 'SINGLE_AND_VOLUME') {
        this._searchForm.getButton('submit').set('visible', false);
        this.addChild(this._grid);
        this.removeChild(this._description);
        if (values.class.trim() === '') {
          const classWidget = this._searchForm.getWidget('class');
          classWidget.reset();
          values.class = classWidget.get('value');
        }
        values.school = this.getSchoolId();
        values.licenseType = this.selectedLicenseType;
        this._grid.filter(values);
        this._grid.resize();
      }
    },

    toogleNotification: function(message) {
      const notificationWidget = this._searchForm.getWidget('NotificationText');
      if (message) {
        notificationWidget.set('visible', true);
        notificationWidget.set(
            'content',
            '<p>' + entities.encode(_(message)) + '</p>',
        );
      } else {
        notificationWidget.set('visible', false);
        notificationWidget.set('content', '');
      }
    },

    onChooseDifferentWorkgroup: function(workingGroupId) {
      const classWidget = this._searchForm.getWidget('class');
      const workgroupWidget = this._searchForm.getWidget('workgroup');
      if (this.selectedLicenseType === 'WORKGROUP')
        this.setButtonDisabled(
            this.isButtonDisabled(classWidget, workgroupWidget),
        );

      //clear existing notification
      this.toogleNotification('');
      if (
          classWidget &&
          classWidget.value !== '__all__' &&
          workingGroupId !== '__all__'
      ) {
        classWidget.reset();
        this.toogleNotification(
            'You can either choose Class or Workgroup, Class has been reset.',
        );
      }
    },

    onChooseDifferentClass: function(classId) {
      const workgroupWidget = this._searchForm.getWidget('workgroup');
      const classWidget = this._searchForm.getWidget('class');
      if (this.selectedLicenseType === 'WORKGROUP')
        this.setButtonDisabled(this.isButtonDisabled(workgroupWidget, classWidget));

      //clear existing notification
      this.toogleNotification('');
      if (
          workgroupWidget &&
          workgroupWidget.value !== '__all__' &&
          classId !== '__all__'
      ) {
        workgroupWidget.reset();
        this.toogleNotification(
            'You can either choose Class or Workgroup, Workgroup has been reset.',
        );
      }
    },

    onChooseLicenseType: function(licenseType) {
      this.toogleNotification('');
      this.removeChild(this._grid);
      this.addChild(this._description);
      this._searchForm.getButton('submit').set('visible', true);
      switch (licenseType) {
        case 'SCHOOL':
          this.selectedLicenseType = 'SCHOOL';
          this._searchForm.getWidget('class').set('visible', false);
          this._searchForm.getWidget('workgroup').set('visible', false);
          this._searchForm.getWidget('pattern').set('visible', false);
          this.setButtonDisabled(false);
          break;
        case 'WORKGROUP':
          this.selectedLicenseType = 'WORKGROUP';
          this._searchForm.getWidget('pattern').set('visible', false);
          this._searchForm.getWidget('class').set('visible', true);
          this._searchForm.getWidget('workgroup').set('visible', true);
          let isButtonDisabled = this.isButtonDisabled(
              this._searchForm.getWidget('class'),
              this._searchForm.getWidget('workgroup'),
          );
          this.setButtonDisabled(isButtonDisabled);
          break;
        default:
          this.selectedLicenseType = 'SINGLE_AND_VOLUME';
          this._searchForm.getWidget('class').set('visible', true);
          this._searchForm.getWidget('workgroup').set('visible', true);
          this._searchForm.getWidget('pattern').set('visible', true);
          this.setButtonDisabled(false);
      }
    },

    onBackBtnClick: function() {
      this.toogleNotification('');
      this.removeChild(this._grid);
      const licenseTypeWidget = this._searchForm.getWidget('licenseType');
      licenseTypeWidget.reset();
      this.addChild(this._searchForm);
    },

    isButtonDisabled: function(schoolClass, workgroup) {
      isDisabled = false;
      console.log([schoolClass.value, workgroup.value]);
      if (schoolClass.value === '__all__' && workgroup.value === '__all__') {
        isDisabled = true;
      }
      return isDisabled;
    },

    setButtonDisabled: function(disable) {
      this._searchForm.getButton('submit').set('disabled', disable);
    },

    afterPageChange: function() {
      this.removeChild(this._grid);
      if (this._searchForm) {
        this.removeChild(this._searchForm);
      }

      const notificationWidget = {
        type: Text,
        size: 'One',
        name: 'NotificationText',
        content: '',
        visible: false,
      };

      const workgroupWidget = {
        type: ComboBox,
        name: 'workgroup',
        staticValues: [{id: '__all__', label: _('All workgroups')}],
        dynamicValues: 'licenses/workgroups',
        dynamicOptions: {
          school: this.getSchoolId(),
        },
        label: _('Workgroup'),
        description: _(
            'Select a workgroup or enter free text (e.g. a part of a workgroup name)',
        ),
        size: 'OneFourth',
        onChange: lang.hitch(this, function(values) {
          this.onChooseDifferentWorkgroup(values);
        }),
      };

      const classWidget = {
        type: SuggestionBox,
        name: 'class',
        staticValues: [{id: '__all__', label: _('All classes')}],
        dynamicValues: 'licenses/classes',
        dynamicOptions: {
          school: this.getSchoolId(),
        },
        label: _('Class'),
        description: _(
            'Select a class or enter free text (e.g. a part of a class name)',
        ),
        size: 'OneFourth',
        onChange: lang.hitch(this, function(values) {
          this.onChooseDifferentClass(values);
        }),
      };

      const widgets = [
        {
          type: ComboBox,
          name: 'licenseType',
          label: _('License type'),
          staticValues: [
            {id: 'SINGLE_AND_VOLUME', label: _('Single- / Volumelicense')},
            {
              id: 'WORKGROUP',
              label: _('Workgroup license'),
            },
            {
              id: 'SCHOOL',
              label: _('School license'),
            },
          ],
          size: 'OneFourth',
          onChange: lang.hitch(this, function(values) {
            this.onChooseLicenseType(values);
          }),
        },
        classWidget,
        workgroupWidget,
        notificationWidget,
        {
          type: SearchBox,
          name: 'pattern',
          label: _('User'),
          inlineLabel: _('Search user'),
          size: 'OneFourth',
          onSearch: lang.hitch(this, function() {
            this._searchForm.submit();
          }),
        },
      ];

      this._searchForm = new SearchForm({
        name: 'searchForm',
        region: 'nav',
        widgets: widgets,
        buttons: [
          {
            name: 'submit',
            label: _('Next'),
            visible: true,
            disable: true,
          },
        ],
        layout: [
          ['licenseType', 'class', 'workgroup', 'pattern', 'submit'],
          ['NotificationText'],
        ],
        onSearch: lang.hitch(this, function(values) {
          switch (this.selectedLicenseType) {
            case 'SCHOOL':
              this.setSchoolAssignment();
              break;
            case 'WORKGROUP':
              let className =
                this._searchForm.getWidget("class").displayedValue;
              let workgroupName =
                this._searchForm.getWidget("workgroup").displayedValue;

              if (values.class !== '__all__') {
                this.setGroup(values.class, className, 'schoolClass');
              } else if (values.workgroup !== '__all__') {
                this.setGroup(values.workgroup, workgroupName, 'workgroup');
              }
              break;
            case 'SINGLE_AND_VOLUME':
              this.onSearchSubmit(values);
          }
        }),
      });

      const actions = [
        {
          name: 'allocate',
          label: _('To media selection'),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: true,
          callback: lang.hitch(this, function() {
            this.setUserIds(this._grid.getSelectedIDs());
          }),
        },
      ];
      const columns = [
        {
          name: 'username',
          label: _('Username'),
        },
        {
          name: 'lastname',
          label: _('Last name'),
        },
        {
          name: 'firstname',
          label: _('First name'),
        },
        {
          name: 'role',
          label: _('Role'),
        },
        {
          name: 'class',
          label: _('Class'),
        },
        {
          name: 'workgroup',
          label: _('Workgroup'),
        },
      ];
      this._grid = new Grid({
        actions: actions,
        columns: columns,
        moduleStore: store('username', 'licenses/users'),
      });

      this.addChild(this._searchForm);
    },

    buildRendering: function() {
      this.inherited(arguments);
      this._description = new _Description({});
      this.addChild(this._description);
    },
  });
});
