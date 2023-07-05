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
      'dojo/date/locale',
      'umc/i18n!umc/modules/licenses'],
    function(declare, lang, domClass, dateLocale, _) {
      return declare('umc.modules.licenses.LicenseColumns', [], {
        getColumns: function() {
          return [
            {
              name: 'licenseCode', label: _('LC'), width: '35px',
              formatter: lang.hitch(this, 'formatInvalid'),
            }, {
              name: 'productId',
              label: _('Medium ID'),
              width: '155px',
              formatter: lang.hitch(this, function(value, license) {
                if (value && value.startsWith('urn:bilo:medium:')) {
                  value = value.slice(16, value.length);
                }
                return value;
              }),
            }, {
              name: 'productName', label: _('Medium'), width: '475px',
            }, {
              name: 'publisher', label: _('PB'), width: '50px',
            }, {
              name: 'licenseTypeLabel', label: _('LT'), width: '30px',
            }, {
              name: 'for', label: _('L'), width: '20px',
            }, {
              name: 'countAquired', label: _('Max'), width: '45px',
            }, {
              name: 'countAssigned', label: _('As.'), width: '45px',
              formatter: lang.hitch(this, 'formatActivated'),
            }, {
              name: 'countAvailable', label: _('Av.'), width: '45px',
            }, {
              name: 'importDate',
              label: _('Import'),
              width: '95px',
              formatter: lang.hitch(this, function(value, license) {
                if (value) {
                  value = dateLocale.format(new Date(value), {
                    fullYear: true, selector: 'date',
                  });
                }
                return value;
              }),
            }];
        },
      });
    });
