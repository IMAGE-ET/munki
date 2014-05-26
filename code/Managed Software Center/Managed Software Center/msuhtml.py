# encoding: utf-8
#
#  msuhtml.py
#  Managed Software Center
#
#  Created by Greg Neagle on 2/24/14.
#

import os

from operator import itemgetter
from random import shuffle
from urllib import quote, unquote
from string import Template

import MunkiItems
import msulib
import msulog
import munki

from AppKit import NSApp
from Foundation import NSBundle
from Foundation import NSLocalizedString


def get_template(template_name, raw=False):
    '''return an html template. If raw is True, just return the string; otherwise
    return a string Template object'''
    customTemplatesPath = os.path.join(msulib.html_dir(), 'custom/templates')
    resourcesPath = NSBundle.mainBundle().resourcePath()
    defaultTemplatesPath = os.path.join(resourcesPath, 'templates')
    for directory in [customTemplatesPath, defaultTemplatesPath]:
        templatePath = os.path.join(directory, template_name)
        if os.path.exists(templatePath):
            try:
                file_ref = open(templatePath)
                template_html = file_ref.read()
                file_ref.close()
                if raw:
                    return template_html.decode('utf-8')
                else:
                    return Template(template_html.decode('utf-8'))
            except (IOError, OSError):
                return None
    return None

def build_page(filename):
    '''Dispatch request to build a page to the appropriate function'''
    name = os.path.splitext(filename)[0]
    key, p, quoted_value = name.partition('-')
    value = unquote(quoted_value)
    if key == 'detail':
        build_detail_page(value)
    elif key == 'category':
        build_list_page(category=value)
    elif key == 'categories':
        build_categories_page()
    elif key == 'filter':
        build_list_page(filter=value)
    elif key == 'developer':
        build_list_page(developer=value)
    elif key == 'myitems':
        build_myitems_page()
    elif key == 'updates':
        build_updates_page()
    elif key == 'updatedetail':
        build_updatedetail_page(value)
    else:
        build_item_not_found_page(filename)


def write_page(page_name, html):
    '''write html to page_name in our local html directory'''
    html_file = os.path.join(msulib.html_dir(), page_name)
    f = open(html_file, 'w')
    f.write(html.encode('utf-8'))
    f.close()


def assemble_page(main_page_template_name, page_dict, **kwargs):
    '''Returns HTML for our page from one or more templates
       and a dictionary of keys and values'''
    # get our main template
    main_page = get_template(main_page_template_name)
    # incorporate any sub-templates
    html_template = Template(main_page.safe_substitute(**kwargs))
    # substitute page variables
    html = html_template.safe_substitute(page_dict)
    return html


def generate_page(page_name, main_page_template_name, page_dict, **kwargs):
    '''Assembles HTML and writes the page to page_name in our local html directory'''
    html = assemble_page(main_page_template_name, page_dict, **kwargs)
    write_page(page_name, html)


def addSidebarLabels(page):
    '''adds localized labels for the detail view sidebars'''
    page['informationLabel'] = NSLocalizedString(
                                    u"Information",
                                    u"Sidebar Information label")
    page['categoryLabel'] = NSLocalizedString(
                                    u"Category:",
                                    u"Sidebar Category label")
    page['versionLabel'] = NSLocalizedString(
                                    u"Version:",
                                    u"Sidebar Version label")
    page['sizeLabel'] = NSLocalizedString(
                                    u"Size:",
                                    u"Sidebar Size label")
    page['developerLabel'] = NSLocalizedString(
                                    u"Developer:",
                                    u"Sidebar Developer label")
    page['statusLabel'] = NSLocalizedString(
                                    u"Status:", u"Sidebar Status label")
    page['moreByDeveloperLabel'] = NSLocalizedString(
                                    u"More by %s",
                                    u"Sidebar More By Developer label")
    page['moreInCategoryLabel'] = NSLocalizedString(
                                    u"More in %s",
                                    u"Sidebar More In Category label")
    page['typeLabel'] = NSLocalizedString(
                                    u"Type:", u"Sidebar Type label")
    page['dueLabel'] = NSLocalizedString(
                                    u"Due:", u"Sidebar Due label")


def build_item_not_found_page(page_name):
    '''Build item not found page'''
    page = {}
    page['item_not_found_message'] = NSLocalizedString(
        u"Cannot display the requested item.", u"Item Not Found message")
    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'page_not_found_template.html', page, footer=footer)


def build_detail_page(item_name):
    '''Build page showing detail for a single optional item'''
    items = MunkiItems.getOptionalInstallItems()
    page_name = u'detail-%s.html' % item_name
    for item in items:
        if item['name'] == item_name:
            page = MunkiItems.OptionalItem(item)
            addSidebarLabels(page)
            # make "More in CategoryFoo" list
            page['hide_more_in_category'] = u'hidden'
            more_in_category_html = u''
            more_in_category = []
            if item.get('category'):
                category = item['category']
                page['category_link'] = u'category-%s.html' % quote(category)
                more_in_category = [a for a in items
                                    if a.get('category') == category
                                    and a != item
                                    and a.get('status') != 'installed']
                if more_in_category:
                    page['hide_more_in_category'] = u''
                    page['moreInCategoryLabel'] = page['moreInCategoryLabel'] % page['category']
                    shuffle(more_in_category)
                    more_template = get_template('detail_more_items_template.html')
                    for more_item in more_in_category[:4]:
                        more_item['second_line'] = more_item.get('developer', '')
                        more_in_category_html += more_template.safe_substitute(more_item)
            page['more_in_category'] = more_in_category_html
            # make "More by DeveloperFoo" list
            page['hide_more_by_developer'] = u'hidden'
            more_by_developer_html = u''
            more_by_developer = []
            if item.get('developer'):
                developer = item['developer']
                page['developer_link'] = (u'developer-%s.html' % quote(developer))
                more_by_developer = [a for a in items
                                     if a.get('developer') == developer
                                     and a != item
                                     and a not in more_in_category
                                     and a.get('status') != 'installed']
                if more_by_developer:
                    page['hide_more_by_developer'] = u''
                    page['moreByDeveloperLabel'] = (
                        page['moreByDeveloperLabel'] % developer)
                    shuffle(more_by_developer)
                    more_template = get_template(
                                        'detail_more_items_template.html')
                    for more_item in more_by_developer[:4]:
                        more_item['second_line'] = more_item.get('category', '')
                        more_by_developer_html += more_template.safe_substitute(more_item)
            page['more_by_developer'] = more_by_developer_html
            footer = get_template('footer_template.html', raw=True)
            generate_page(page_name, 'detail_template.html', page, footer=footer)
            return
    msulog.debug_log('No detail found for %s' % item_name)
    build_item_not_found_page(page_name)


def build_list_page(category=None, developer=None, filter=None):
    '''Build page listing available optional items'''
    items = MunkiItems.getOptionalInstallItems()

    header = u'All items'
    page_name = u'category-all.html'
    if category == 'all':
        category = None
    if category:
        header = category
        page_name = u'category-%s.html' % category
    if developer:
        header = developer
        page_name = u'developer-%s.html' % developer
    if filter:
        header = u'Search results for %s' % filter
        page_name = u'filter-%s.html' % filter

    category_list = []
    for item in items:
        if 'category' in item and item['category'] not in category_list:
            category_list.append(item['category'])

    item_html = build_list_page_items_html(
                            category=category, developer=developer, filter=filter)

    # make HTML for Categories pop-up menu
    if category:
        categories_html = u'<option>All Categories</option>\n'
    else:
        categories_html = u'<option selected>All Categories</option>\n'

    for item in sorted(category_list):
        if item == category:
            categories_html += u'<option selected>%s</option>\n' % item
        else:
            categories_html += u'<option>%s</option>\n' % item

    categories_html_list = ''
    # make HTML for list of categories
    for item in sorted(category_list):
        categories_html_list += u'<li class="link"><a href="category-%s.html">%s</a></li>\n' % (
                                                                                 quote(item), item)

    page = {}
    page['list_items'] = item_html
    page['category_items'] = categories_html
    page['category_list'] = categories_html_list
    page['header_text'] = header
    if category or filter or developer:
        showcase = ''
    else:
        showcase = get_template('showcase_template.html', raw=True)
    sidebar = get_template('sidebar_template.html', raw=True)
    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'list_template.html', page,
                  showcase=showcase, sidebar=sidebar, footer=footer)


def build_list_page_items_html(category=None, developer=None, filter=None):
    '''Returns HTML for the items on the list page'''
    items = MunkiItems.getOptionalInstallItems()
    item_html = u''
    if filter:
        items = [item for item in items
                 if filter in item['display_name'].lower()
                 or filter in item['description'].lower()
                 or filter in item['developer'].lower()
                 or filter in item['category'].lower()]
    if category:
        items = [item for item in items
                 if category.lower() in item.get('category', '').lower()]
    if developer:
        items = [item for item in items
                 if developer.lower() in item.get('developer', '').lower()]

    if items:
        item_template = get_template('list_item_template.html')
        for item in sorted(items, key=itemgetter('display_name_lower')):
            item_html += item_template.safe_substitute(item)
        # pad with extra empty items so we have a multiple of 3
        if len(items) % 3:
            for x in range(3 - (len(items) % 3)):
                item_html += u'<div class="lockup"></div>\n'
    else:
        # no items; build appropriate alert messages
        status_results_template = get_template('status_results_template.html')
        alert = {}
        if filter:
            alert['primary_status_text'] = NSLocalizedString(
                u"Your search had no results.",
                u"No Search Results primary text")
            alert['secondary_status_text'] = NSLocalizedString(
                u"Try searching again.", u"No Search Results secondary text")
        elif category:
            alert['primary_status_text'] = NSLocalizedString(
                u"There are no items in this category.",
                u"No Category Results primary text")
            alert['secondary_status_text'] = NSLocalizedString(
                u"Try selecting another category.",
                u"No Category Results secondary text")
        elif developer:
            alert['primary_status_text'] = NSLocalizedString(
                u"There are no items from this developer.",
                u"No Developer Results primary text")
            alert['secondary_status_text'] = NSLocalizedString(
                u"Try selecting another developer.",
                u"No Developer Results secondary text")
        else:
            alert['primary_status_text'] = NSLocalizedString(
               u"There are no available software items.",
               u"No Items primary text")
            alert['secondary_status_text'] = NSLocalizedString(
               u"Try again later.",
               u"No Items secondary text")
        alert['hide_progress_bar'] = u'hidden'
        alert['progress_bar_value'] = u''
        item_html = status_results_template.safe_substitute(alert)
    return item_html


def build_categories_page():
    '''Build page showing available categories and some items in each one'''
    all_items = MunkiItems.getOptionalInstallItems()
    header = u'Categories'
    page_name = u'categories.html'
    category_list = []
    for item in all_items:
        if 'category' in item and item['category'] not in category_list:
            category_list.append(item['category'])

    item_html = build_category_items_html()

    categories_html = u'<option selected>All Categories</option>\n'
    for item in sorted(category_list):
        categories_html += u'<option>%s</option>\n' % item

    page = {}
    page['list_items'] = item_html
    page['category_items'] = categories_html
    page['header_text'] = header
    
    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'list_template.html', page, showcase=u'', sidebar=u'', footer=footer)


def build_category_items_html():
    '''Returns HTML for the items on the Categories page'''
    all_items = MunkiItems.getOptionalInstallItems()
    if all_items:
        category_list = []
        for item in all_items:
            if 'category' in item and item['category'] not in category_list:
                category_list.append(item['category'])

        item_template = get_template('category_item_template.html')
        item_html = u''
        for category in sorted(category_list):
            category_data = {}
            category_data['category_name'] = category
            category_data['category_link'] = u'category-%s.html' % quote(category)
            category_items = [item for item in all_items if item.get('category') == category]
            shuffle(category_items)
            category_data['item1_icon'] = category_items[0]['icon']
            category_data['item1_display_name'] = category_items[0]['display_name']
            category_data['item1_detail_link'] = category_items[0]['detail_link']
            if len(category_items) > 1:
                category_data['item2_display_name'] = category_items[1]['display_name']
                category_data['item2_detail_link'] = category_items[1]['detail_link']
            else:
                category_data['item2_display_name'] = u''
                category_data['item2_detail_link'] = u'#'
            if len(category_items) > 2:
                category_data['item3_display_name'] = category_items[2]['display_name']
                category_data['item3_detail_link'] = category_items[2]['detail_link']
            else:
                category_data['item3_display_name'] = u''
                category_data['item3_detail_link'] = u'#'

            item_html += item_template.safe_substitute(category_data)

        # pad with extra empty items so we have a multiple of 3
        if len(category_list) % 3:
            for x in range(3 - (len(category_list) % 3)):
                item_html += u'<div class="lockup"></div>\n'

    else:
        # no items
        status_results_template = get_template('status_results_template.html')
        alert = {}
        alert['primary_status_text'] = NSLocalizedString(
            u"There are no available software items.",
            u"No Items primary text")
        alert['secondary_status_text'] = NSLocalizedString(
            u"Try again later.",
            u"No Items secondary text")
        alert['hide_progress_bar'] = u'hidden'
        alert['progress_bar_value'] = u''
        item_html = status_results_template.safe_substitute(alert)
    return item_html


def build_myitems_page():
    '''Builds "My Items" page, which shows all current optional choices'''
    page_name = u'myitems.html'

    page = {}
    page['my_items_header_label'] = NSLocalizedString(
        u"My Items", u"My Items Header label")
    page['myitems_rows'] = build_myitems_rows()
    
    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'myitems_template.html', page, footer=footer)


def build_myitems_rows():
    '''Returns HTML for the items on the 'My Items' page'''
    item_list = MunkiItems.getMyItemsList()
    if item_list:
        item_template = get_template('myitems_row_template.html')
        myitems_rows = u''
        for item in sorted(item_list, key=itemgetter('display_name_lower')):
            myitems_rows += item_template.safe_substitute(item)
    else:
        status_results_template = get_template('status_results_template.html')
        alert = {}
        alert['primary_status_text'] = NSLocalizedString(
            u"You have no selected software.",
            u"No Installed Software primary text")
        alert['secondary_status_text'] = (
            u'<a href="category-all.html">%s</a>' % NSLocalizedString(
                                                        u"Select software to install.",
                                                        u"No Installed Software secondary text"))
        alert['hide_progress_bar'] = u'hidden'
        myitems_rows = status_results_template.safe_substitute(alert)
    return myitems_rows


def build_updates_page():
    '''available/pending updates'''
    page_name = u'updates.html'
    
    # need to consolidate/centralize this flag. Accessing it this way is ugly.
    if NSApp.delegate().mainWindowController._update_in_progress:
        return build_update_status_page()

    item_list = MunkiItems.getEffectiveUpdateList()

    other_updates = [
        item for item in MunkiItems.getOptionalInstallItems()
        if item['status'] == 'update-available']

    page = {}
    page['update_rows'] = u''
    page['hide_progress_spinner'] = u'hidden'
    page['hide_other_updates'] = u'hidden'
    page['install_all_button_classes'] = u''
    
    item_template = get_template('update_row_template.html')

    if item_list:
        for item in item_list:
            page['update_rows'] += item_template.safe_substitute(item)
    elif not other_updates:
        status_results_template = get_template('status_results_template.html')
        alert = {}
        alert['primary_status_text'] = NSLocalizedString(
             u"Your software is up to date.", u"No Pending Updates primary text")
        alert['secondary_status_text'] = NSLocalizedString(
             u"There is no new software for your computer at this time.",
             u"No Pending Updates secondary text")
        alert['hide_progress_bar'] = u'hidden'
        alert['progress_bar_value'] = u''
        page['update_rows'] = status_results_template.safe_substitute(alert)

    count = len(item_list)
    page['update_count'] = msulib.updateCountMessage(count)
    page['install_btn_label'] = msulib.getInstallAllButtonTextForCount(count)
    page['warning_text'] = get_warning_text()

    page['other_updates_header_message'] = NSLocalizedString(
        u"Other available updates",
        u"Other Available Updates label")
    page['other_update_rows'] = u''

    if other_updates:
        page['hide_other_updates'] = u''
        for item in other_updates:
            page['other_update_rows'] += item_template.safe_substitute(item)
    
    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'updates_template.html', page, footer=footer)


def build_update_status_page():
    '''returns our update status page'''
    page_name = u'updates.html'
    item_list = []
    other_updates = []
    
    status_title_default = NSLocalizedString(u"Checking for updates...",
                                             u"Checking For Updates message")
    page = {}
    page['update_rows'] = u''
    page['hide_progress_spinner'] = u''
    page['hide_other_updates'] = u'hidden'
    page['other_updates_header_message'] = u''
    page['other_update_rows'] = u''
    
    # don't like this bit as it ties us to a different object
    status_controller = NSApp.delegate().statusController
    status_results_template = get_template('status_results_template.html')
    alert = {}
    alert['primary_status_text'] = (
        status_controller._status_message
        or NSLocalizedString(u"Update in progress.", u"Update In Progress primary text"))
    alert['secondary_status_text'] = (status_controller._status_detail or '&nbsp;')
    alert['hide_progress_bar'] = u''
    if status_controller._status_percent < 0:
        alert['progress_bar_attributes'] = u'class="indeterminate"'
    else:
        alert['progress_bar_attributes'] = (u'style="width: %s%%"'
                                            % status_controller._status_percent)
    page['update_rows'] = status_results_template.safe_substitute(alert)
    
    install_all_button_classes = []
    if status_controller._status_stopBtnHidden:
        install_all_button_classes.append(u'hidden')
    if status_controller._status_stopBtnDisabled:
        install_all_button_classes.append(u'disabled')
    page['install_all_button_classes'] = u' '.join(install_all_button_classes)

    # don't like this bit as it ties us yet another object
    page['update_count'] = NSApp.delegate().mainWindowController._status_title or status_title_default
    page['install_btn_label'] = NSLocalizedString(u"Cancel", u"Cancel button title")
    page['warning_text'] = u''

    footer = get_template('footer_template.html', raw=True)
    generate_page(page_name, 'updates_template.html', page, footer=footer)


def getRestartActionForUpdateList(update_list):
    '''Returns a localized overall restart action message for the list of updates'''
    if [item for item in update_list if 'Restart' in item.get('RestartAction', '')]:
        # found at least one item containing 'Restart' in its RestartAction
        return NSLocalizedString(u"Restart Required", u"Require Restart message")
    if [item for item in update_list if 'Logout' in item.get('RestartAction', '')]:
        # found at least one item containing 'Logout' in its RestartAction
        return NSLocalizedString(u"Logout Required", u"Require Logout message")
    else:
        return ''


def get_warning_text():
    '''Return localized text warning about forced installs and/or
        logouts and/or restarts'''
    item_list = MunkiItems.getEffectiveUpdateList()
    warning_text = u''
    forced_install_date = munki.earliestForceInstallDate(item_list)
    if forced_install_date:
        date_str = munki.stringFromDate(forced_install_date)
        forced_date_text = NSLocalizedString(
                            u"One or more items must be installed by %s",
                            u"Forced Install Date summary")
        warning_text = forced_date_text % date_str
    restart_text = getRestartActionForUpdateList(item_list)
    if restart_text:
        if warning_text:
            warning_text += u' &bull; ' + restart_text
        else:
            warning_text = restart_text
    return warning_text


def build_updatedetail_page(identifier):
    '''Build detail page for a non-optional update'''
    items = MunkiItems.getUpdateList()
    page_name = u'updatedetail-%s.html' % identifier
    name, sep, version = identifier.partition('--version-')
    for item in items:
        if item['name'] == name and item['version_to_install'] == version:
            page = MunkiItems.UpdateItem(item)
            addSidebarLabels(page)
            force_install_after_date = item.get('force_install_after_date')
            if force_install_after_date:
                local_date = munki.discardTimeZoneFromDate(
                                                force_install_after_date)
                date_str = munki.shortRelativeStringFromDate(
                                                local_date)
                page['dueLabel'] += u' '
                page['short_due_date'] = date_str
            else:
                page['dueLabel'] = u''
                page['short_due_date'] = u''

            footer = get_template('footer_template.html', raw=True)
            generate_page(page_name, 'updatedetail_template.html', page, footer=footer)
            return
    # if we get here we didn't find any item matching identifier
    msulog.debug_log('No update detail found for %s' % item_name)
    build_item_not_found_page(page_name)

