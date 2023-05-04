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
  'dojo/dom-class',
  'dojo/on',
  'dojo/date/locale',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dijit/_WidgetBase',
  'dijit/_TemplatedMixin',
  'umc/tools',
  'umc/dialog',
  '../../common/Page',
  'umc/widgets/Grid',
  'umc/widgets/CheckBox',
  'umc/widgets/ContainerWidget',
  'put-selector/put',
  'umc/i18n!umc/modules/licenses',
], function(
    declare,
    lang,
    domClass,
    on,
    dateLocale,
    Memory,
    Observable,
    _WidgetBase,
    _TemplatedMixin,
    tools,
    dialog,
    Page,
    Grid,
    CheckBox,
    ContainerWidget,
    put,
    _,
) {
  const _Table = declare(
      'umc.modules.licenses.license.DetailPage',
      [_WidgetBase, _TemplatedMixin],
      {
        //// overwrites
        templateString: `
			<div class="licensesTable">
				<div
					class="licensesTable__coverWrapper"
				>
					<div
						data-dojo-attach-point="_coverFallbackNode"
						class="licensesTable__coverFallback"
					></div>
					<img
						data-dojo-attach-point="_coverNode"
						class="licensesTable__cover"
					>
				</div>
				<div
					data-dojo-attach-point="_tableNode"
					class="licensesTable__data"
				></div>
			</div>
		`,

        //// self
        standbyDuring: null, // required

        license: null,
        _setLicenseAttr: function(license) {
          domClass.remove(this._coverFallbackNode, 'dijitDisplayNone');
          domClass.add(this._coverNode, 'dijitDisplayNone');
          if (license.cover) {
            this._coverFallbackNode.innerHTML = _('Loading cover...');
            const img = new Image();
            on(
                img,
                'load',
                lang.hitch(this, function() {
                  domClass.add(this._coverFallbackNode, 'dijitDisplayNone');
                  domClass.remove(this._coverNode, 'dijitDisplayNone');
                  this._coverNode.src = license.cover;
                }),
            );
            on(
                img,
                'error',
                lang.hitch(this, function() {
                  this._coverFallbackNode.innerHTML = _('No cover available');
                }),
            );
            img.src = license.cover;
          } else {
            this._coverFallbackNode.innerHTML = _('No cover available');
          }

          this._tableNode.innerHTML = '';

          function e(id) {
            let val = license[id];
            if (val === null) {
              val = '';
            }
            if (typeof val === 'string') {
              val = val || '---';
            }
            if (id === 'productId' && val.startsWith('urn:bilo:medium:')) {
              val = val.slice(16, val.length);
            }
            return val;
          }

          function d(id) {
            let date = license[id];
            if (date) {
              date = dateLocale.format(new Date(date), {
                fullYear: true,
                selector: 'date',
              });
            } else {
              date = '---';
            }
            return date;
          }

          function validityStatus(id) {
            let val = license[id];

            if (val) {
              val = _('valid') || _('invalid');
            }

            return val;
          }

          function usageStatus(id) {
            let val = license[id];

            if (val) {
              val = _('activated') || _('not activated');
            }

            return val;
          }

          function expiryDate() {
            if (license['expiryDate']) {
              return d('expiryDate');
            }

            if (license['usageStatus']) {
              return _('unlimited');
            } else {
              return _('undefined');
            }
          }

          const ignore = lang.hitch(this, function ignore() {
            this._ignore = new CheckBox({
              value: license.ignore,
              onChange: lang.hitch(this, function() {
                this.onIgnoreCheckBoxClicked();
              }),
            });
            return this._ignore.domNode;
          });

          const data = [
            [
              [_('Title'), e('productName')],
              [
                _('Author'),
                e('author')],
              [
                _('Publisher'),
                e('publisher')],
              [
                _('Medium ID'),
                e('productId')],
              [
                _('License code'),
                e('licenseCode')],
              [
                _('License type'),
                e('licenseTypeLabel')],
              [
                _('Special license'),
                e('specialLicense')],
              [_('Reference'), e('reference')],
              [_('Usage'), e('usage')],
            ],
            [
              [_('Ignore'), ignore()],
              [
                _('Delivery'),
                d('importDate')],
              [
                _('Validity start'),
                d('validityStart')],
              [
                _('Validity end'),
                d('validityEnd')],
              [
                _('Validity span'),
                e('validitySpan')],
              [
                _('Max. Users'),
                e('countAquired')],
              [
                _('Available'),
                e('countAvailable')],
              [_('Assigned'), e('countAssigned')],
              [_('Expired'), e('countExpired')],
            ],
            [
              [_('Validity status'), validityStatus('validityStatus')],
              [_('Usage status'), usageStatus('usageStatus')],
              [_('Expiry date'), expiryDate()],
            ],
          ];

          for (const column of data) {
            let _column = put('div.licensesTable__column');
            for (const row of column) {
              let _row = put('div.licensesTable__row');
              put(_row,
                  'div.licensesTable__dataLabel',
                  row[0],
                  '+ div.licensesTable__dataValue',
                  row[1],
              );
              put(_column, _row);
            }
            put(this._tableNode, _column);
          }

          this._set('license', license);
        },

        onIgnoreCheckBoxClicked: function() {
          // evt stub
        },

        ignoreChanged: function() {
          return this.getIgnore() !== this.license.ignore;
        },

        getIgnore: function() {
          return this._ignore.get('value');
        },
      },
  );

  return declare('umc.modules.licenses.LicenseDetailPage', [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    _table: null,
    _grid: null,

    license: null,
    _setLicenseAttr: function(license) {
      this._table.set('license', license);
      this._grid.moduleStore.setData(license.users);
      this._grid.filter();
      this._set('license', license);
      if (license.licenseType === 'SINGLE' || license.licenseType ===
          'VOLUME') {
        this._grid.set('actions', this._actions);
      } else {
        this._grid.set('actions', []);
      }
    },

    load: function(licenseCode) {
      return this.standbyDuring(
          tools.umcpCommand('licenses/get', {
            licenseCode: licenseCode,
          }).then(
              lang.hitch(this, function(response) {
                const license = response.result;
                this.set('license', license);
                this._headerButtons.save.set('disabled', true);
                return license.licenseCode;
              }),
          ),
      );
    },

    save: function() {
      if (!this._table.ignoreChanged()) {
        this.onBack();
      } else {
        this.standbyDuring(
            tools.umcpCommand('licenses/set_ignore', {
              licenseCode: this.license.licenseCode,
              ignore: this._table.getIgnore(),
            }).then(
                lang.hitch(this, function(response) {
                  const result = response.result;
                  if (result.errorMessage) {
                    dialog.alert(result.errorMessage);
                  } else {
                    this.onBack();
                  }
                }),
            ),
        );
      }
    },

    removeLicenseFromUsers: function(usernames) {
      tools.umcpCommand('licenses/remove_from_users', {
        licenseCode: this.license.licenseCode,
        usernames: usernames,
      }).then(
          lang.hitch(this, function(response) {
            this.load(this.license.licenseCode);
            const failedAssignments = response.result.failedAssignments;
            if (failedAssignments.length) {
              const containerWidget = new ContainerWidget({});
              const container = put(containerWidget.domNode, 'div');
              put(
                  container,
                  'p',
                  _('The license could not be removed from the following users:'),
              );
              const table = put(container, 'table');
              for (let failedAssignment of failedAssignments) {
                const tr = put(table, 'tr');
                put(tr, 'td', failedAssignment.username);
                put(tr, 'td', failedAssignment.error);
              }
              dialog.alert(containerWidget);
            }
          }),
      );
    },

    back: function() {
      if (this._table.ignoreChanged()) {
        dialog.confirm(
            _('There are unsaved changes. Are you sure to cancel?'),
            [
              {
                label: _('Continue editing'),
              },
              {
                label: _('Discard changes'),
                default: true,
                callback: lang.hitch(this, 'onBack'),
              },
            ],
        );
      } else {
        this.onBack();
      }
    },

    onBack: function() {
      // event stub
    },

    //// lifecycle
    postMixInProperties: function() {
      this.headerButtons = [
        {
          name: 'save',
          label: _('Save'),
          callback: lang.hitch(this, 'save'),
        },
        {
          name: 'close',
          label: _('Back'),
          callback: lang.hitch(this, 'back'),
        },
      ];
    },

    buildRendering: function() {
      this.inherited(arguments);

      this._table = new _Table({});
      on(
          this._table,
          'ignoreCheckBoxClicked',
          lang.hitch(this, function() {
            this._headerButtons.save.set(
                'disabled',
                !this._table.ignoreChanged(),
            );
          }),
      );

      this._actions = [
        {
          name: 'delete',
          label: _('Remove assignment'),
          isStandardAction: true,
          isContextAction: true,
          isMultiAction: true,
          canExecute: function(user) {
            return user.status === 'ASSIGNED';
          },
          callback: lang.hitch(this, function(idxs, users) {
            this.removeLicenseFromUsers(
                users.map(function(user) {
                  return user.username;
                }),
            );
          }),
        },
      ];
      const columns = [
        {
          name: 'username',
          label: _('User'),
        },
        {
          name: 'roleLabels',
          label: _('Roles'),
        },
        {
          name: 'classes',
          label: _('Class'),
        },
        {
          name: 'workgroups',
          label: _('Workgroup'),
        },

        {
          name: 'statusLabel',
          label: _('Status'),
        },
        {
          name: 'dateOfAssignment',
          label: _('Date of assignment'),
          visible: false,
          formatter: function(value, object) {
            if (value) {
              value = dateLocale.format(new Date(value), {
                fullYear: true,
                selector: 'date',
              });
            }
            return value;
          },
        },
      ];
      this._grid = new Grid({
        columns: columns,
        moduleStore: new Observable(
            new Memory({
              data: [],
              idProperty: 'username',
            }),
        ),
      });

      this.addChild(this._table);
      this.addChild(this._grid);
    },

    _onShow: function() {
      this._grid.filter();
    },
  });
})
;
