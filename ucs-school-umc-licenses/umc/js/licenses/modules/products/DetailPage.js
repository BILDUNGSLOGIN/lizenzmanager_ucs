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
  'dojo/on',
  'dojo/dom-class',
  'dojo/topic',
  'dojo/date/locale',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dijit/_WidgetBase',
  'dijit/_TemplatedMixin',
  'umc/tools',
  '../../common/Page',
  'umc/widgets/Grid',
  'umc/widgets/StandbyMixin',
  'put-selector/put',
  '../../common/LicenseColumns',
  'umc/i18n!umc/modules/licenses',
], function(
    declare,
    lang,
    on,
    domClass,
    topic,
    dateLocale,
    Memory,
    Observable,
    _WidgetBase,
    _TemplatedMixin,
    tools,
    Page,
    Grid,
    StandbyMixin,
    put,
    LicenseColumns,
    _,
) {
  const _Table = declare(
      'umc.modules.licenses.product.DetailPage',
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
					class="productsTable__data"
				></div>
			</div>
		`,

        //// self
        standbyDuring: null, // required

        product: null,

        _setProductAttr: function(product) {
          domClass.remove(this._coverFallbackNode, 'dijitDisplayNone');
          domClass.add(this._coverNode, 'dijitDisplayNone');
          if (product.cover) {
            this._coverFallbackNode.innerHTML = _('Loading cover...');
            const img = new Image();
            on(
                img,
                'load',
                lang.hitch(this, function() {
                  domClass.add(this._coverFallbackNode, 'dijitDisplayNone');
                  domClass.remove(this._coverNode, 'dijitDisplayNone');
                  this._coverNode.src = product.cover;
                }),
            );
            on(
                img,
                'error',
                lang.hitch(this, function() {
                  this._coverFallbackNode.innerHTML = _('No cover available');
                }),
            );
            img.src = product.cover;
          } else {
            this._coverFallbackNode.innerHTML = _('No cover available');
          }

          this._tableNode.innerHTML = '';

          function e(id) {
            let val = product[id];
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

          const data = [
            [
              [_('Title'), e('title')],
              [_('Author'), e('author')],
              [_('Publisher'), e('publisher')],
              [_('Medium ID'), e('productId')],
              [_('Description'), e('description')],
            ],
            [], [],
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

          this._set('product', product);
        },
      },
  );

  return declare('umc.modules.licenses.ProductDetailPage',
      [Page, LicenseColumns], {
        //// overwrites
        fullWidth: true,

        _table: null,
        _grid: null,

        product: null,

        maxUserSum: '-',
        assignedSum: '-',
        expiredSum: '-',
        availableSum: '-',

        _setProductAttr: function(product) {
          this._table.set('product', product);
          this._grid.moduleStore.setData(product.licenses);
          this._grid.filter();
          this._grid.resize();
          this._set('product', product);
        },

        load: function(productId) {
          return this.standbyDuring(
              tools.umcpCommand('licenses/products/get', {
                school: this.getSchoolId(),
                productId: productId,
              }).then(
                  lang.hitch(this, function(response) {
                    const product = response.result;
                    this.set('product', product);
                  }),
              ),
          );
        },

        onBack: function() {
          // event stub
        },

        //// lifecycle
        postMixInProperties: function() {
          this.inherited(arguments);

          this.headerButtons = [
            {
              name: 'close',
              label: _('Change product'),
              callback: lang.hitch(this, 'onBack'),
            },
          ];
        },

        buildRendering: function() {
          this.inherited(arguments);

          this._table = new _Table({});

          const actions = [
            {
              name: 'edit',
              label: _('Open license'),
              isStandardAction: true,
              isContextAction: true,
              isMultiAction: false,
              callback: lang.hitch(this, function(idxs, licenses) {
                topic.publish(
                    '/umc/modules/open',
                    'licenses',
                    'licenses/licenses',
                    {
                      moduleState: `school:${this.getSchoolId()}:license:${licenses[0].licenseCode}`,
                    },
                );
              }),
            },
          ];


          this._grid = new Grid({
            actions: actions,
            columns: this.getColumns(),
            class: 'licensesTable__licenses',
            moduleStore: new Observable(
                new Memory({
                  data: [],
                  idProperty: 'licenseCode',
                }),
            ),
            addTitleOnCellHoverIfOverflow: true,
            gridOptions: {
              selectionMode: 'single',
            },
            selectorType: 'radio',
          });

          this.addChild(this._table);
          this.addChild(this._grid);
        },

        _onShow: function() {
          this._grid.filter();
        },
      });
});
