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
  'dojo/dom',
  'dojo/dom-class',
  'dojo/aspect',
  'dojo/on',
  'dojo/mouse',
  'dojo/query',
  'dojo/date/locale',
  'dojox/html/entities',
  'dijit/Tooltip',
  'umc/store',
  'umc/tools',
  '../../common/Page',
  'umc/widgets/Grid',
  'umc/widgets/SearchForm',
  'umc/widgets/Form',
  'umc/widgets/Text',
  'umc/widgets/TextBox',
  'put-selector/put',
  'umc/dialog',
  'umc/i18n!umc/modules/licenses',
], function(
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
    tools,
    Page,
    Grid,
    SearchForm,
    Form,
    Text,
    TextBox,
    put,
    dialog,
    _,
) {
  return declare('umc.modules.licenses.import.ImportMediaLicensePage', [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    schoolId: null, // required parameter
    showChangeSchoolButton: false,
    showDebug: false,

    _grid: null,
    _form: null,
    _cache_form: null,
    _searchForm: null,
    _isAdvancedSearch: true,

    alloction: null,
    _setAllocationAttr: function(allocation) {},

    query: function() {
      this.standbyDuring(
          this._form.ready().then(
              lang.hitch(this, function() {
                this._form.submit();
              }),
          ),
      );
    },

    onBack: function() {
      // event stub
    },

    onProductChosen: function() {
      // event stub
    },

    onChangeUsers: function() {
      // event stub
    },

    onChooseDifferentSchool: function() {
      // event stub
    },

    onShowProduct: function(productId) {
      // event stub
    },

    importSuccessful: function(res) {
      const importRes = `<div>${res.licenses.length} ${_(
          'licenses were imported successfully')}.</div>`;
      const jsonRes =
          '<div>License package:</div><pre>' +
          JSON.stringify(res.licenses, undefined, 3) +
          '</pre>';
      const confirmationMsg = importRes + jsonRes;
      dialog.confirm(_(confirmationMsg), [
        {
          label: _('Ok'),
          default: true,
          callback: lang.hitch(this, 'onBack'),
        },
      ]);
      this._form.clearFormValues();
    },

    getImport: function(pickUpNumber) {
      this.standbyDuring(
          tools.umcpCommand('licenses/import/get', {
            school: this.getSchoolId(),
            pickUpNumber: pickUpNumber,
          }).then(
              lang.hitch(this, function(response) {
                const res = response.result;
                if (res.errorMessage) {
                  dialog.alert(result.errorMessage);
                } else {
                  this.importSuccessful(res);
                }
              }),
          ).finally(lang.hitch(this, function() {
            this._form._buttons.submit.set('disabled', false);
          })),
      );
    },

    cacheRebuild: function() {
      tools.umcpCommand('licenses/cache/rebuild', {
        school: this.getSchoolId(),
      }).then(
          lang.hitch(this, function(response) {
            const res = response.result;
            if (res.errorMessage) {
              dialog.alert(result.errorMessage);
            } else {
              if (res.status === 1) {
                dialog.alert(_('Started cache update.'));
              } else if (res.status === 2) {
                dialog.alert(_('Cache update already running.'));
              }
            }
          }),
      );
    },
    cacheRebuildDebug: function() {
      tools.umcpCommand('licenses/cache/rebuild/debug', {
        school: this.getSchoolId(),
      }).then(
          lang.hitch(this, function(response) {
            const res = response.result;
            if (res.errorMessage) {
              dialog.alert(result.errorMessage);
            } else {
              if (res.status === 1) {
                dialog.alert(_('Started cache update.'));
              } else if (res.status === 2) {
                dialog.alert(_('Cache update already running.'));
              }
            }
          }),
      );
    },
    // with msecs: repeat every msecs, without msecs: call only once.
    getCacheStatus: function(msecs = null) {
      tools.umcpCommand('licenses/cache/status', {}).then(
          lang.hitch(this, function(response) {
            try {
              const result = response.result;
              if (result.errorMessage) {
                dialog.alert(result.errorMessage);
              } else {
                this._cache_form.getWidget('last_cache_build').
                    set('content',
                        _('Cache last updated:') + ' ' + result.time);
                if (result.status == true) {
                  this._cache_form.getWidget('cache_build_status').
                      set('content',
                          _('Cache update status:') + ' ' + _('Updating'));
                  this._cache_form.getButton('submit').set('disabled', true);
                } else {
                  this._cache_form.getWidget('cache_build_status').
                      set('content',
                          _('Cache update status:') + ' ' + _('Finished'));
                  this._cache_form.getButton('submit').set('disabled', false);
                }
              }
              if (msecs) {
                window.setTimeout(lang.hitch(this, function() {
                  this.getCacheStatus(msecs);
                }), msecs);
              }
            } catch (e) {}
          }),
      );
    },
    getCacheStatusDebug: function(msecs = null) {
      tools.umcpCommand('licenses/cache/status/debug', {}).then(
          lang.hitch(this, function(response) {
            try {
              const result = response.result;
              if (result.errorMessage) {
                dialog.alert(result.errorMessage);
              } else {
                this._cache_form.getWidget('last_cache_build').
                    set('content',
                        _('Cache last updated:') + ' ' + result.time);
                if (result.status == true) {
                  this._cache_form.getWidget('cache_build_status').
                      set('content',
                          _('Cache update status:') + ' ' + _('Updating'));
                  this._cache_form.getButton('submit').set('disabled', true);
                } else {
                  this._cache_form.getWidget('cache_build_status').
                      set('content',
                          _('Cache update status:') + ' ' + _('Finished'));
                  this._cache_form.getButton('submit').set('disabled', false);
                }
              }
              if (msecs) {
                window.setTimeout(lang.hitch(this, function() {
                  this.getCacheStatusDebug(msecs);
                }), msecs);
              }
            } catch (e) {}
          }),
      );
    },
    addDebug: function() {
      this._cache_debug_form = new Form({
        widgets: [],
        buttons: [
          {
            name: 'submit',
            label: _('Update all cache'),
          },
        ],
      });

      this._cache_debug_form.on(
          'submit',
          lang.hitch(this, function() {
            this.cacheRebuildDebug();
            this.getCacheStatus();
          }),
      );

      this.addChild(this._cache_debug_form);
      this.addChild(new Text({
        'content': _(
            'This is a debug button enabled by ucr variable bildungslogin/debug.'),
      }));
    },

    //// lifecycle
    postMixInProperties: function() {
      this.inherited(arguments);
      const headerButtons = [];
      if (this.showChangeSchoolButton) {
        headerButtons.push({
          name: 'changeSchool',
          label: _('Change school'),
          callback: lang.hitch(this, 'onChooseDifferentSchool'),
        });
      }

      this.headerButtons = headerButtons;
    },

    buildRendering: function() {
      this.inherited(arguments);

      this._form = new Form({
        widgets: [
          {
            type: TextBox,
            name: 'pickUpNumber',
            label: _('Pick-up number for licence data package'),
            size: 'TwoThirds',
            description: _(
                'Please enter the collection number for the licence data package you wish to import. You received the collection number at the end of the purchase process or with the order confirmation for the licences.',
            ),
          },
        ],
        buttons: [
          {
            name: 'submit',
            label: _('Import licences'),
          },
        ],
      });
      this._form.on(
          'submit',
          lang.hitch(this, function() {
            const values = this._form.getValues();
            const pickUpNumber = values.pickUpNumber;
            this._form._buttons.submit.set('disabled', true);
            this.getImport(pickUpNumber);
          }),
      );

      this._cache_form = new Form({
        widgets: [
          {
            type: Text,
            name: 'last_cache_build',
            content: _('Cache last updated:'),
          },
          {
            type: Text,
            name: 'cache_build_status',
            content: _('Cache update status:'),
          },
        ],
        buttons: [
          {
            name: 'submit',
            label: _('Update cache'),
          },
        ],
      });

      this._cache_form.on(
          'submit',
          lang.hitch(this, function() {
            this.cacheRebuild();
            this.getCacheStatus();
          }),
      );

      this.getCacheStatus(10000);

      this.addChild(this._form);
      this.addChild(new Text({
        'content': _(
            'After importing new licenses, an update via the "Update cache" button is also required.'),
      }));
      this.addChild(new Text({
        'content': _(
            'This process can take a long time if you have a large number of licenses.'),
      }));
      this.addChild(this._cache_form);
      this.addChild(new Text({
        'content': _(
            'This button is also used to update the cache after creating/deleting users or study groups.'),
      }));

      tools.ucr('bildungslogin/debug').
          then(lang.hitch(this, function(data) {
            if (data['bildungslogin/debug'] === 'true') {
              this.addDebug();
            }
          }));
    },
  });
});
