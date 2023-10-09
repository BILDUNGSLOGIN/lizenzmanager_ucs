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
        'dojo/on',
        'dojo/date/locale',
        'dojo/Deferred',
        'dojox/html/entities',
        'dijit/Tooltip',
        'umc/dialog',
        'umc/store',
        'umc/tools',
        '../../common/Page',
        'umc/widgets/Grid',
        'umc/widgets/CheckBox',
        'umc/widgets/DateBox',
        'umc/widgets/ComboBox',
        'umc/widgets/SearchForm',
        'umc/widgets/Text',
        'umc/widgets/TextBox',
        'umc/widgets/SuggestionBox',
        'umc/widgets/ProgressInfo',
        'umc/widgets/Form',
        '../../common/LicenseColumns',
        'umc/i18n!umc/modules/licenses'],
    function (declare, lang, dom, domClass, on, dateLocale, Deferred, entities,
              Tooltip, dialog, store, tools, Page, Grid, CheckBox, DateBox, ComboBox,
              SearchForm, Text, TextBox, SuggestionBox, ProgressInfo, Form,
              LicenseColumns, _) {
        return declare('umc.modules.licenses.LicenseSearchPage',
            [Page, LicenseColumns], {
                //// overwrites
                fullWidth: true,

                //// self
                standbyDuring: null, // required parameter
                schoolId: null, // required parameter
                moduleFlavor: null, // required parameter
                showChangeSchoolButton: false,
                allocation: '',
                allocation_chunksize: 60,	// default if UCR variable is not set

                _licenseTypes: [], // reference to the currently active grid
                _grid: null,
                _gridFooter: null,
                _gridAllocation: null,
                _gridGroup: null,
                _searchForm: null,

                _isAdvancedSearch: false,

                maxUserSum: '-',
                assignedSum: '-',
                expiredSum: '-',
                availableSum: '-',

                // temp variables for progress display
                _wrap_assign_function: null,
                _wrap_assign_arg: null,
                _wrap_assign_max: null,
                _wrap_assign_items: null,
                _wrap_assign_args: null,
                _wrap_assign_chunksize: null,
                _wrap_assign_deferred: null,
                _wrap_assign_result: null,
                _wrap_assign_progress: null,

                // Wraps the backend calls to assign_<something> such that it features:
                //
                //  *   a busy state (user-visible state: i'm working right now)
                //  *   the capability to split the call into several calls and to collect
                //      their results
                //  *   a percentual sign of progress
                //
                // Function returns a Deferred with the result, so it is a full replacement
                // to the original UMCP command call.
                _wrap_assign: function (umcp_function, args, chunksize = 1) {

                    this._wrap_assign_deferred = new Deferred();    // do this first

                    var arg_to_split = 'usernames';     // currently only for users
                    var usernames = args[arg_to_split]; // requested users. Will be replaced soon...

                    // get the list of unassigned users, and refuse to start the assignment if the licenses will not suffice
                    this._not_assigned_users(usernames, args['licenseCodes']).then(lang.hitch(this, function (result) {
                        var usernames = result.result;
                        // If the reduction yielded no user who would need the license: we should not call the assignment
                        // handler for NO USERS. Prepare a different message for this case.
                        if (usernames.length == 0) {
                            var response = {'result': {'nothingToDo': true}};
                            this._wrap_assign_deferred.resolve(response);
                            return;
                        }
                        var new_args = {
                            'usernames': usernames,
                            'licenseCodes': args['licenseCodes'],
                        };

                        // Check if licenses will suffice, and bail out if not
                        var avail = this._licenses_selected();
                        if (avail < usernames.length) {
                            this._wrap_assign_deferred.cancel(
                                _('Assigning licenses to %d users failed',
                                    usernames.length));
                            return;
                        }

                        // From here onwards, the status variables have to be object-global to our
                        // 'this' object instance, so the wrap_assign_handler() function can pick them
                        // up and change them. We prepend '_wrap_assign_' to all these variable names.
                        this._wrap_assign_function = umcp_function;
                        this._wrap_assign_arg = arg_to_split;
                        // This must be a copy, or else the original selection is being emptied!
                        this._wrap_assign_items = Object.create(usernames);
                        this._wrap_assign_max = usernames.length;
                        this._wrap_assign_args = new_args;
                        this._wrap_assign_chunksize = chunksize;
                        this._wrap_assign_result = {
                            'countSuccessfulAssignments': 0,
                            'notEnoughLicenses': false,
                            'failedAssignments': [],
                            'validityInFuture': [],
                        };

                        // ET-67: It makes no sense to show the progress bar if the number of to-be-assigned
                        //	users fits into one chunk size... HERE is the point to check for this condition
                        if (usernames.length <= chunksize) {
                            this._wrap_assign_progress = null;	// so the _wrap_assign_handler knows it should
                            // NOT set percentage info and show the simple spinner instead
                            this._wrap_assign_handler();
                            this.standbyDuring(this._wrap_assign_deferred);
                        } else {
                            // Make a progress bar
                            this._wrap_assign_progress = new ProgressInfo(
                                {maximum: usernames.length});
                            // umc.web's Progressinfo discards all constructor arguments, even 'maximum' :-(
                            this._wrap_assign_progress._progressBar.set('maximum',
                                usernames.length);

                            this._wrap_assign_progress.update(
                                0,
                                _('Licenses are being processed. Please have a little patience.'));

                            this._wrap_assign_handler();

                            this.standbyDuring(this._wrap_assign_deferred,
                                this._wrap_assign_progress);
                        }
                    }));        // FIXME make an error handler that will resolve the deferred with an error message

                    return this._wrap_assign_deferred;
                },

                // Helper function for wrap_assign: it maintains the status variables
                // while a request is underway. This function will call umcpCommand with
                // one chunk of items, and reschedule itself until there are no items left.
                _wrap_assign_handler: function () {
                    var temp_request = this._wrap_assign_args;
                    var temp_items = [];
                    while ((temp_items.length < this._wrap_assign_chunksize) &&
                    (this._wrap_assign_items.length > 0)) {
                        temp_items.push(this._wrap_assign_items.pop());
                    }
                    temp_request[this._wrap_assign_arg] = temp_items;
                    tools.umcpCommand(this._wrap_assign_function, temp_request).then(lang.hitch(this, function (result) {

                        // merge result into global result
                        this._wrap_assign_result['countSuccessfulAssignments'] += result['result']['countSuccessfulAssignments'];
                        // If the limit kicks in: stop immediately.
                        if (result['result']['notEnoughLicenses']) {
                            this._wrap_assign_result['notEnoughLicenses'] = true;
                            this._wrap_assign_items = [];
                        }

                        // update progress bar, but only if there's one
                        if (this._wrap_assign_progress) {
                            this._wrap_assign_progress.update(
                                this._wrap_assign_result['countSuccessfulAssignments'],
                                this._wrap_assign_result['countSuccessfulAssignments'] +
                                ' of ' + this._wrap_assign_max +
                                ' licenses assigned');
                        }

                        if (result['result']['failedAssignments']) {
                            this._wrap_assign_result['failedAssignments'] = result['result']['failedAssignments'];
                        }

                        // If there are items left: start next loop iteration.
                        // If not: finish this loop, and return result.
                        if (this._wrap_assign_items.length > 0) {
                            this._wrap_assign_handler();
                        } else {
                            // clean up progress display?
                            if (this._wrap_assign_progress) {
                                this._wrap_assign_progress.destroyRecursive();
                            }
                            var result = {
                                'error': null,
                                'message': null,
                                'reason': null,
                                'result': this._wrap_assign_result,
                            };
                            this._wrap_assign_deferred.resolve(result);
                        }
                    }), lang.hitch(this, function (result) {
                        alert('something went wrong');
                    }));
                },

                _not_assigned_users: function (usernames, licenseCodes) {
                    // reduce the list of selected usernames to those who do not have any
                    // of the selected license codes assigned. This is done by UMCP. The
                    // function will at least be called after the 'assign licenses' button
                    // but before we start splitting the user list into chunks. Since we know
                    // the 'available' counts of the selected licenses we can decide in advance
                    // if the chunked assignment really CAN come to a successful end.
                    //
                    // NOTE: Only for volume licenses, this function will reduce the number of 'licenses needed'
                    //		because this does not work for any other license types.
                    // NOTE: because umcpCommand IS a deferred we cannot wait for it to be fulfilled here
                    return tools.umcpCommand('licenses/not_assigned_users', {
                        'usernames': usernames, 'licenseCodes': licenseCodes,
                    });
                },

                // check if the requested count of licenses is really available, and disable/enable the
                // action button accordingly. Note that umc.web's grid does not pass all selected items to
                // one callback: therefore we have to retrieve all selected items and sum their 'countAvailable'
                // properties, and return the global permission on each and every item.
                _can_assign_licenses: function (obj) {
                    // ET-67: currently we cannot decide IN ADVANCE, so allow pushing the button and
                    //	defer the real calculation into the backend (TODO: write the backend function)
                    return true;
                },

                // return the sum of 'available' counts of all selected licenses.
                _licenses_selected: function () {
                    var counted = 0;
                    this._grid.getSelectedItems().forEach(function (item) {
                        counted += parseInt(item['countAvailable']);
                    });
                    return counted;
                },

                // return the codes of selected licenses
                _license_codes_selected: function () {
                    var result = [];
                    this._grid.getSelectedItems().forEach(function (item) {
                        result.push(item['licenseCode']);
                    });
                    return result;
                },

                // formats the status text for the assignment grid
                _allocation_footer: function (nItems) {
                    if (!nItems) {
                        return '';
                    }
                    var counted = this._licenses_selected();
                    msg = '';
                    if (counted === 1) {
                        msg += _('One license selected');
                    } else {
                        msg += _('%d licenses selected', counted);
                    }

                    return msg;
                },

                _toggleSearch: function () {
                    this._isAdvancedSearch = !this._isAdvancedSearch;
                    // toggle visibility
                    if (this.getAssignmentType() === 'user') {
                        [
                            'timeFrom',
                            'timeTo',
                            'onlyAvailableLicenses',
                            'publisher',
                            'licenseType',
                            'userPattern',
                            'productId',
                            'product',
                            'licenseCode',
                            'workgroup',
                            'class'].forEach(lang.hitch(this, function (widgetName) {
                            const widget = this._searchForm.getWidget(widgetName);
                            if (widget) {
                                widget.set('visible', this._isAdvancedSearch);
                            }
                        }));
                    } else {
                        [
                            'timeFrom',
                            'timeTo',
                            'onlyAvailableLicenses',
                            'publisher',
                            'userPattern',
                            'productId',
                            'product',
                            'licenseCode',
                            'workgroup',
                            'class'].forEach(lang.hitch(this, function (widgetName) {
                            const widget = this._searchForm.getWidget(widgetName);
                            if (widget) {
                                widget.set('visible', this._isAdvancedSearch);
                            }
                        }));
                    }

                    this._searchForm.getWidget('pattern').set('visible', !this._isAdvancedSearch);

                    // update toggle button
                    const button = this._searchForm.getButton('toggleSearch');
                    if (this._isAdvancedSearch) {
                        button.set('iconClass', 'umcDoubleLeftIcon');
                    } else {
                        button.set('iconClass', 'umcDoubleRightIcon');
                    }
                },

                updateText: function () {
                    domClass.remove(this._assignmentText.domNode, 'dijitDisplayNone');
                    if (this.getAssignmentType() === 'user') {

                        this.removeChild(this._gridGroup);
                        this.addChild(this._gridAllocation);
                        this._grid = this._gridAllocation;

                        const count = this.getUserIds().length;
                        const id = this.id + '-tooltip';
                        const msg = `
				<p>
					${entities.encode(
                            count === 1 ? _('Assign licenses to 1 selected user.') : _(
                                'Assign licenses to %s selected users.', count))}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_('show selected users'))})
					</span>
				</p>
				<p>
					${entities.encode(_('Choose the licenses you want to assign.'))}
				</p>
			`.trim();
                        this._assignmentText.set('content', msg);
                        const node = dom.byId(id);
                        on(node, 'click', lang.hitch(this, function (evt) {
                            let label = '';
                            for (const username of this.getUserIds()) {
                                label += `<div>${entities.encode(username)}</div>`;
                            }
                            Tooltip.show(label, node);
                            evt.stopImmediatePropagation();
                            on.once(window, 'click', lang.hitch(this, function (event) {
                                Tooltip.hide(node);
                            }));
                        }));
                    } else if (this.getAssignmentType() === 'school') {
                        this.removeChild(this._gridAllocation);
                        this.addChild(this._gridGroup);
                        this._grid = this._gridGroup;
                        const id = this.id + '-tooltip';
                        const msg = `
				<p>
					${entities.encode(_('Assign licenses to selected school.'))}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_('show selected school'))})
					</span>
				</p>
				<p>
					${entities.encode(_('Choose the licenses you want to assign.'))}
				</p>
			`.trim();
                        this._assignmentText.set('content', msg);
                        const node = dom.byId(id);
                        on(node, 'click', lang.hitch(this, function (evt) {
                            let label = `<div>${entities.encode(
                                this.getSchoolId())}</div>`;

                            Tooltip.show(label, node);
                            evt.stopImmediatePropagation();
                            on.once(window, 'click', lang.hitch(this, function (event) {
                                Tooltip.hide(node);
                            }));
                        }));
                    } else if (this.getAssignmentType() === 'workgroup' ||
                        this.getAssignmentType() === 'schoolClass') {
                        this.removeChild(this._gridAllocation);
                        this.addChild(this._gridGroup);
                        this._grid = this._gridGroup;
                        const id = this.id + '-tooltip';
                        let assignmentLabel = entities.encode(
                            _('Assign licenses to selected workgroup/class.'));
                        if (this.getUserCount()) {
                            assignmentLabel = entities.encode(
                                this.getUserCount() === 1 ? _(
                                    'Assign licenses to 1 selected user.') : _(
                                    'Assign licenses to %s selected users.',
                                    this.getUserCount()));
                        }
                        const msg = `
				<p>
					${assignmentLabel}
					<span id="${id}" class="licensesShowSelection">
						(${entities.encode(_('show selected workgroup/class'))})
					</span>
				</p>
				<p>
					${entities.encode(_('Choose the licenses you want to assign.'))}
				</p>
			`.trim();
                        this._assignmentText.set('content', msg);
                        const node = dom.byId(id);
                        on(node, 'click', lang.hitch(this, function (evt) {
                            let label = '';
                            label = `<div>${entities.encode(this.getGroupName())}</div>`;
                            Tooltip.show(label, node);
                            evt.stopImmediatePropagation();
                            on.once(window, 'click', lang.hitch(this, function (event) {
                                Tooltip.hide(node);
                            }));
                        }));
                    }
                },

                query: function () {
                    this.standbyDuring(// Deactivated in this flavor due to Issue #97
                        this._searchForm.ready().then(lang.hitch(this, function () {
                            this._searchForm.submit();
                        })));
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
                    values.school = this.getSchoolId();
                    values.isAdvancedSearch = true;
                    values.onlyAvailableLicenses = true;
                    if (this.getAssignmentType() === 'user') {
                        values.allocationProductId = this.getProductId();
                        if (values.licenseType === '') {
                            values.licenseType = ['SINGLE', 'VOLUME'];
                        } else if (values.licenseType === 'SINGLE') {
                            values.licenseType = ['SINGLE'];
                        } else if (values.licenseType === 'VOLUME') {
                            values.licenseType = ['VOLUME'];
                        }
                    } else if (this.getAssignmentType() === 'school') {
                        values.licenseType = ['SCHOOL'];
                    } else if (['schoolClass', 'workgroup'].includes(
                        this.getAssignmentType())) {
                        values.allocationProductId = this.getProductId();
                        values.licenseType = ['WORKGROUP'];
                    }
                    this._grid.filter(values);
                    values.licenseType = '';
                },

                // allow only either class or workgroup to be set
                onChooseDifferentClass: function () {
                    const workgroupWidget = this._searchForm.getWidget('workgroup');
                    workgroupWidget.setValue('');
                },
                onChooseDifferentWorkgroup: function () {
                    const classWidget = this._searchForm.getWidget('class');
                    classWidget.setValue('');
                },

                //// lifecycle
                postMixInProperties: function () {
                    this.inherited(arguments);
                    this._licenseTypes = [
                        {id: '', label: ''},
                        {id: 'SINGLE', label: _('Single license')},
                        {id: 'VOLUME', label: _('Volume license')}];
                },

                afterPageChange: function () {
                    this.updateText();
                    this.refreshGrid(this._searchForm.value);
                },

                exportToExcel: function (values) {
                    values.isAdvancedSearch = this._isAdvancedSearch;
                    values.school = this.getSchoolId();
                    values.isAdvancedSearch = true;
                    values.onlyAvailableLicenses = true;

                    if (this.getAssignmentType() === 'user') {
                        values.allocationProductId = this.getProductId();
                        if (values.licenseType === '') {
                            values.licenseType = ['SINGLE', 'VOLUME'];
                        } else if (values.licenseType === 'SINGLE') {
                            values.licenseType = ['SINGLE'];
                        } else if (values.licenseType === 'VOLUME') {
                            values.licenseType = ['VOLUME'];
                        }
                    } else if (this.getAssignmentType() === 'school') {
                        values.licenseType = ['SCHOOL'];
                    } else if (['schoolClass', 'workgroup'].includes(
                        this.getAssignmentType())) {
                        values.allocationProductId = this.getProductId();
                        values.licenseType = ['WORKGROUP'];
                    }

                    tools.umcpCommand('licenses/export_to_excel', values).then(lang.hitch(this, function (response) {
                        const res = response.result;
                        if (res.errorMessage) {
                            dialog.alert(result.errorMessage);
                        } else {
                            downloadFile(res.URL, 'license.xlsx');
                        }
                        this._excelExportForm._buttons.submit.set('disabled',
                            false);
                    }));
                },

                buildRendering: function () {
                    this.inherited(arguments);

                    // retrieve chunksize from UCR if present.
                    tools.ucr('bildungslogin/assignment/chunksize').then(lang.hitch(this, function (data) {
                        this.allocation_chunksize = data['bildungslogin/assignment/chunksize'];
                    }));

                    this._assignmentText = new Text({
                        region: 'nav', class: 'dijitDisplayNone',
                    });

                    const widgets = [
                        {
                            type: DateBox,
                            name: 'timeFrom',
                            visible: false,
                            label: _('Start import period'),
                            size: 'TwoThirds',
                        }, {
                            type: DateBox,
                            name: 'timeTo',
                            label: _('End import period'),
                            size: 'TwoThirds',
                            visible: false,
                        }, {
                            type: ComboBox,
                            name: 'licenseType',
                            label: _('License type'),
                            staticValues: this._licenseTypes,
                            size: 'TwoThirds',
                            visible: false,
                        }, {
                            type: TextBox,
                            name: 'userPattern',
                            label: _('User ID'),
                            description: _(
                                'Search for licenses that have this user assigned. (Searches for \'first name\', \'last name\' and \'username\')'),
                            size: 'TwoThirds',
                            visible: false,
                        }, {
                            type: TextBox,
                            name: 'licenseCode',
                            label: _('License code'),
                            size: 'TwoThirds',
                            visible: false,
                        }, {
                            type: TextBox,
                            name: 'pattern',
                            label: '&nbsp;',
                            inlineLabel: _('Search licenses'),
                        }];
                    widgets.push({
                        type: TextBox,
                        name: 'product',
                        label: _('Media Title'),
                        size: 'TwoThirds',
                        visible: false,
                    }, {
                        type: TextBox,
                        name: 'productId',
                        label: _('Medium ID'),
                        size: 'TwoThirds',
                        visible: false,
                        formatter: function (value) {
                            if (value && value.startsWith('urn:bilo:medium:')) {
                                value = value.slice(16, value.length);
                            }
                            return value;
                        },
                    }, {
                        type: CheckBox,
                        name: 'onlyAvailableLicenses',
                        label: _('Only assignable licenses'),
                        value: false,
                        size: 'TwoThirds',
                        visible: false,
                    }, {
                        type: ComboBox,
                        name: 'publisher',
                        label: _('Publisher'),
                        staticValues: [{id: '', label: ''}],
                        dynamicValues: 'licenses/publishers',
                        dynamicOptions: {
                            school: this.getSchoolId(),
                        },
                        size: 'TwoThirds',
                        visible: false,
                    }, {
                        type: ComboBox,
                        name: 'workgroup',
                        label: _('Assigned to Workgroup'),
                        staticValues: [{id: '', label: ''}],
                        dynamicValues: 'licenses/workgroups',
                        dynamicOptions: {
                            school: this.getSchoolId(),
                        },
                        size: 'TwoThirds',
                        visible: false,
                        onChange: lang.hitch(this, function (values) {
                            this.onChooseDifferentWorkgroup(values);
                        }),
                    }, {
                        type: SuggestionBox,
                        name: 'class',
                        label: _('Assigned to Class'),
                        staticValues: [{id: '', label: ''}],
                        dynamicValues: 'licenses/classes',
                        dynamicOptions: {
                            school: this.getSchoolId(),
                        },
                        size: 'TwoThirds',
                        visible: false,
                        onChange: lang.hitch(this, function (values) {
                            this.onChooseDifferentClass(values);
                        }),
                    });

                    let layout = null;
                    layout = [
                        ['timeFrom', 'timeTo', 'userPattern'], [
                            'licenseType',
                            'licenseCode',
                            'pattern',
                            'submit',
                            'toggleSearchLabel',
                            'toggleSearch']];
                    const buttons = [
                        {
                            name: 'toggleSearch', labelConf: {
                                class: 'umcFilters',
                            }, label: _('Filters'), iconClass: 'umcDoubleRightIcon',

                            callback: lang.hitch(this, function () {
                                this._toggleSearch();
                            }),
                        }];
                    this._searchForm = new SearchForm({
                        class: 'umcUDMSearchForm umcUDMSearchFormSimpleTextBox',
                        region: 'nav',
                        widgets: widgets,
                        buttons: buttons,
                        layout: layout,
                        onSearch: lang.hitch(this, function (values) {
                            this.refreshGrid(values);
                        }),
                    });
                    domClass.add(
                        this._searchForm.getWidget('licenseCode').$refLabel$.domNode,
                        'umcSearchFormElementBeforeSubmitButton');

                    const actions = [];
                    actions.push({
                        name: 'assign',
                        label: _('Assign licenses'),
                        isStandardAction: true,
                        isContextAction: true,
                        isMultiAction: true,
                        canExecute: lang.hitch(this, '_can_assign_licenses'),
                        callback: lang.hitch(this, function (_idxs, licenses) {
                            if (this.getAssignmentType() === 'user') {
                                // Call a wrapper function, for chunked action and a progress bar.
                                this._wrap_assign('licenses/assign_to_users', {
                                    licenseCodes: licenses.map(
                                        (license) => license.licenseCode), // Use the already-reduced list of users who really need the license.
                                    // ET-67: we cannot calculate this in advance; so take ALL selected users instead.
                                    usernames: this.getUserIds(),
                                }, this.allocation_chunksize).then(lang.hitch(this, function (response) {
                                    const result = response.result;

                                    let msg = '';
                                    if (result.notEnoughLicenses) {
                                        msg += '<p>' + entities.encode(
                                                _('The number of selected licenses is not sufficient to assign a license to all selected users. Therefore, no licenses have been assigned. Please reduce the number of selected users or select more licenses and repeat the process.')) +
                                            '</p>';
                                        dialog.alert(msg, _('Assigning licenses failed'));
                                        return;
                                    }
                                    if (result.nothingToDo) {
                                        dialog.alert('<p>' +
                                            _('All selected users already have the requested license. Therefore, nothing had to be done.') +
                                            '</p>', _('No assignment needed'));
                                        return;
                                    }
                                    if (result.countSuccessfulAssignments) {
                                        if (result.countSuccessfulAssignments ===
                                            this.getUserIds().length) {
                                            msg += '<p>' + entities.encode(
                                                    _('Licenses were successfully assigned to all %s selected users.',
                                                        result.countSuccessfulAssignments)) +
                                                '</p>';
                                        } else {
                                            msg += '<p>' + entities.encode(
                                                _('Licenses were successfully assigned to %s of the %s selected users. The remaining users already had the license.',
                                                    result.countSuccessfulAssignments,
                                                    this.getUserIds().length)) + '</p>';
                                        }
                                    }
                                    if (result.failedAssignments.length) {
                                        msg += '<p>';
                                        msg += result.countSuccessfulAssignments > 0
                                            ? entities.encode(
                                                _('Some selected users could not be assigned licenses:'))
                                            : entities.encode(
                                                _('Failed to assign licenses to the selected users:'));
                                        msg += '<ul>';
                                        for (const error of result.failedAssignments) {
                                            msg += '<li>' + entities.encode(error) + '</li>';
                                        }
                                        msg += '</ul>';
                                        msg += '</p>';
                                    }
                                    if (result.validityInFuture.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Warning: The validity for the following assigned licenses lies in the future:'));
                                        msg += '<ul>';
                                        for (const licenseCode of result.validityInFuture) {
                                            msg += '<li>' + entities.encode(licenseCode) +
                                                '</li>';
                                        }
                                        msg += '</ul>';
                                        msg += '</p>';
                                    }
                                    const title = _('Assigning licenses');
                                    dialog.alert(msg, title);
                                    // Should we refresh the grid to reflect the new counters?
                                    this.refreshGrid(this._searchForm.value);
                                }), function (message) {
                                    dialog.alert(
                                        _('The number of selected licenses is not sufficient to assign a license to all selected users. Therefore, no licenses have been assigned. Please reduce the number of selected users or select more licenses and repeat the process.'),
                                        message);

                                });
                            } else if (this.getAssignmentType() === 'school') {
                                let school = this.getSchoolId();

                                tools.umcpCommand('licenses/assign_to_school', {
                                    licenseCodes: licenses.map(
                                        (license) => license.licenseCode),
                                    school: school,
                                }).then(lang.hitch(this, function (response) {
                                    const result = response.result;
                                    let msg = '';
                                    if (result.notEnoughLicenses) {
                                        msg += '<p>' + entities.encode(
                                                _('The number of selected licenses is not sufficient to assign a license to the selected school.')) +
                                            '</p>';
                                        dialog.alert(msg, _('Assigning licenses failed'));
                                        return;
                                    }
                                    if (result.countSuccessfulAssignments) {
                                        msg += '<p>' + entities.encode(
                                            _('Licenses were successfully assigned to selected school.',
                                                result.countSuccessfulAssignments)) + '</p>';
                                    }
                                    if (result.failedAssignments.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Failed to assign licenses to the selected school.'));
                                        for (const error of result.failedAssignments) {
                                            msg += '<li>' + entities.encode(error) + '</li>';
                                        }
                                        msg += '</p>';
                                    }
                                    if (result.validityInFuture.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Warning: The validity for the following assigned licenses lies in the future:'));
                                        msg += '<ul>';
                                        for (const licenseCode of result.validityInFuture) {
                                            msg += '<li>' + entities.encode(licenseCode) +
                                                '</li>';
                                        }
                                        msg += '</ul>';
                                        msg += '</p>';
                                    }

                                    const title = _('Assigning licenses');
                                    dialog.alert(msg, title);
                                }));
                            } else if (this.getAssignmentType() === 'schoolClass') {
                                tools.umcpCommand('licenses/assign_to_class', {
                                    licenseCodes: licenses.map(
                                        (license) => license.licenseCode),
                                    schoolClass: this.getGroup().substr(3, this.getGroup().indexOf(',') - 3),
                                }).then(lang.hitch(this, function (response) {
                                    const result = response.result;
                                    let msg = '';
                                    if (result.notEnoughLicenses) {
                                        msg += '<p>' + entities.encode(
                                                _('The number of selected licenses is not sufficient to assign a license to the selected class.')) +
                                            '</p>';
                                        dialog.alert(msg, _('Assigning licenses failed'));
                                        return;
                                    }
                                    if (result.countSuccessfulAssignments) {
                                        msg += '<p>' + entities.encode(
                                            _('Licenses were successfully assigned to selected class.',
                                                result.countSuccessfulAssignments)) + '</p>';
                                    }
                                    if (result.failedAssignments.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Failed to assign licenses to the selected class.'));
                                        for (const error of result.failedAssignments) {
                                            msg += '<li>' + entities.encode(error) + '</li>';
                                        }
                                        msg += '</p>';
                                    }
                                    if (result.validityInFuture.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Warning: The validity for the following assigned licenses lies in the future:'));
                                        msg += '<ul>';
                                        for (const licenseCode of result.validityInFuture) {
                                            msg += '<li>' + entities.encode(licenseCode) +
                                                '</li>';
                                        }
                                        msg += '</ul>';
                                        msg += '</p>';
                                    }

                                    const title = _('Assigning licenses');
                                    dialog.alert(msg, title);
                                }));
                            } else if (this.getAssignmentType() === 'workgroup') {
                                tools.umcpCommand('licenses/assign_to_workgroup', {
                                    licenseCodes: licenses.map(
                                        (license) => license.licenseCode),
                                    workgroup: this.getGroup().substr(3, this.getGroup().indexOf(',') - 3),
                                }).then(lang.hitch(this, function (response) {
                                    const result = response.result;
                                    let msg = '';
                                    if (result.notEnoughLicenses) {
                                        msg += '<p>' + entities.encode(
                                                _('The number of selected licenses is not sufficient to assign a license to the selected workgroup.')) +
                                            '</p>';
                                        dialog.alert(msg, _('Assigning licenses failed'));
                                        return;
                                    }
                                    if (result.countSuccessfulAssignments) {
                                        msg += '<p>' + entities.encode(
                                            _('Licenses were successfully assigned to selected workgroup.',
                                                result.countSuccessfulAssignments)) + '</p>';
                                    }
                                    if (result.failedAssignments.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Failed to assign licenses to the selected workgroup.'));
                                        for (const error of result.failedAssignments) {
                                            msg += '<li>' + entities.encode(error) + '</li>';
                                        }
                                        msg += '</p>';
                                    }
                                    if (result.validityInFuture.length) {
                                        msg += '<p>';
                                        msg += entities.encode(
                                            _('Warning: The validity for the following assigned licenses lies in the future:'));
                                        msg += '<ul>';
                                        for (const licenseCode of result.validityInFuture) {
                                            msg += '<li>' + entities.encode(licenseCode) +
                                                '</li>';
                                        }
                                        msg += '</ul>';
                                        msg += '</p>';
                                    }

                                    const title = _('Assigning licenses');
                                    dialog.alert(msg, title);
                                }));
                            }
                        }),
                    });

                    this._gridAllocation = new Grid({
                        actions: actions,
                        columns: this.getColumns(),
                        moduleStore: store('licenseCode', 'licenses'),
                        sortIndex: -10,
                        addTitleOnCellHoverIfOverflow: true,
                        footerFormatter: lang.hitch(this, '_allocation_footer'),
                    });

                    this._gridGroup = new Grid({
                        actions: actions,
                        columns: this.getColumns(),
                        moduleStore: store('licenseCode', 'licenses'),
                        sortIndex: -10,
                        addTitleOnCellHoverIfOverflow: true,
                        gridOptions: {
                            selectionMode: 'single',
                        },
                        selectorType: 'radio',
                    });

                    this._excelExportForm = new Form({
                        widgets: [], buttons: [
                            {
                                name: 'submit',
                                label: _('Export'),
                                style: 'margin-top:20px',
                            }],
                    });

                    this._excelExportForm.on('submit', lang.hitch(this, function () {
                        this._excelExportForm._buttons.submit.set('disabled', true);
                        values = this._searchForm.value;
                        values.school = this.getSchoolId();
                        values.pattern = this._searchForm.value.pattern;
                        this.exportToExcel(values);
                    }));

                    this.addChild(this._assignmentText);
                    this.addChild(this._searchForm);
                    this.addChild(this._excelExportForm);

                    this.addChild(this._gridAllocation);
                    this._grid = this._gridAllocation;
                },
            });
    });
