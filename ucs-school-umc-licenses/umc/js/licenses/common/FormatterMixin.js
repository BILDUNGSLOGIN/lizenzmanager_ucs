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
      return declare('umc.modules.licenses.FormatterMixin', [], {
        _today: new Date(),

        formatInvalid: function(value, license) {
          if(license && license.validityStatus === '0') {
            return `<span class="bildungslogin-red">${value}</span>`;
          } else {
            return value;
          }
        },

        formatActivated: function(value, license) {
          if(license && license.usageStatus === '1') {
            return `<span class="bildungslogin-green">${value}</span>`;
          } else {
            return value;
          }
        },

        formatExpired(value, license) {
          if (license && license.expiryDate) {
            let date = new Date(license.expiryDate)

            if (date <= this._today) {
              return `<span class="bildungslogin-red">${value}</span>`;
            }
          }
          return value;
        },
      });
    });
