#!/usr/bin/python3
# Tool to automagically create ebooks from Wildbow's online source of Worm
# Zoetrophy 2016


"""
RTF documentation:
    https://www.safaribooksonline.com/library/view/rtf-pocket-guide/9781449302047/ch01.html
    https://www.safaribooksonline.com/library/view/rtf-pocket-guide/9781449302047/ch04.html
    http://www.biblioscape.com/rtf15_spec.htm
    https://msdn.microsoft.com/en-us/library/aa140277(office.10).aspx
"""


import argparse
from lxml import etree
from lxml import html
import os
import random
import re
from urllib import request
import time
from urllib import parse as urlparse


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-a', '--arc', metavar='ARC#', nargs='*', type=int,
                        help='select arc(s) to download (by index, not by title)')
arg_parser.add_argument('-c', '--chapter', metavar='CHAP#', nargs='*', type=int,
                        help='select chapter(s) to download (by index, not by title)')
arg_parser.add_argument('-d', '--download', action='store_true',
                        help='explicitly set to download mode')
arg_parser.add_argument('-j', '--join', action='store_true',
                        help='join all files of the same arc')
arg_parser.add_argument('-s', '--seconds', metavar='SECONDS', type=int,
                        help='time to wait after page load in seconds (automatically fuzzed)')
arg_parser.add_argument('-f', '--faithful', action='store_true',
                        help='use original chapter titles instead of reformatted ones')
arg_parser.add_argument('-v', '--verbose', action='store_true',
                        help='display more verbose output for debugging')
arg_parser.add_argument('-x', '--debug', action='store_true',
                        help='display only errors and debugging messages')
args = arg_parser.parse_args()


class Constant:
    INDEX_URL = 'https://parahumans.wordpress.com/table-of-contents/'
    USER_AGENT_STRING = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.13' \
                        '(KHTML, like Gecko) Chrome/9.0.597.19 Safari/534.13'


class Typesetting:
    font = {  # Use only fonts present on your machine.
        'primary': {
            'typeface': 'Times New Roman',
            'size': 28
        },
        'header': {
            'typeface': 'Helvetica',
            'size': 26
        },
        'footer': {
            'typeface': 'Helvetica',
            'size': 26
        },
        'chapter_title': {
            'typeface': 'Courier',
            'size': 56
        },
        'chapter_subtitle': {
            'typeface': 'Courier',
            'size': 28
        },
        'chapter_end': {
            'typeface': 'Courier',
            'size': 28
        },
        'cover_title': {
            'typeface': 'Helvetica',
            'size': 72
        },
        'cover_author': {
            'typeface': 'Courier',
            'size': 42
        },
        'cover_other': {
            'typeface': 'Arial',
            'size': 28
        }
    }
    page_margins = {
        'top': 1620,
        'bottom': 1600,
        'left': 1440,
        'right': 1400
    }
    indent = 360
    padding = 1080


class RTF:
    file_header = '{\\rtf1\\deflang1033\\plain\\fs%d\\widowctrl\\hyphauto\\ftnbj\n' % (
        Typesetting.font['primary']['size']
    )
    cover_image_file = 'spider_eyes.txt'
    inner_cover_file = 'inner_cover.txt'
    line_prefix = '{\\pard\\sl360\\slmult1'
    line_suffix = '\\par}\n'
    substitutions = [
        [r'(<em>)|(<i>)', r'\\i '],
        [r'(</em>)|(</i>)', r'\\i0 '],
        [r'(<strong>)|(<b>)', r'\\b '],
        [r'(</strong>)|(</b>)', r'\\b0 '],
        [r'((<br/>)|(<br />)|(<br>))', r'\\line\n'],
        [r'((<p)|(</p)).*?(>)', r''],
        [r'((<a)|(</a)).*?(>)', r''],
        [r'(<del>).*?(</del>)', r''],
        [r'((<del)|(</del)|(<del/)).*?(>)', r''],
        [r'(<em/>)|(<i/>)', r''],
        [r'(<strong/>)|(<b/>)', r'']
    ]
    character_substitutions = [
        [r'(&#160;)', r'\\~'],
        [r'(&#199;)', r'Ç'],
        [r'(&#220;)', r'Ü'],
        [r'(&#224;)', r'à'],
        [r'(&#225;)', r'á'],
        [r'(&#227;)', r'ã'],
        [r'(&#228;)', r'ä'],
        [r'(&#232;)', r'è'],
        [r'(&#233;)', r'é'],
        [r'(&#234;)', r'ê'],
        [r'(&#235;)', r'ë'],
        [r'(&#236;)', r'ì'],
        [r'(&#237;)', r'í'],
        [r'(&#242;)', r'ò'],
        [r'(&#245;)', r'õ'],
        [r'(&#246;)', r'ö'],
        [r'(&#249;)', r'ù'],
        [r'(&#250;)', r'ú'],
        [r'(&#252;)', r'ü'],
        [r'(&#257;)', r'ā'],
        [r'(&#275;)', r'ē'],
        [r'(&#283;)', r'ě'],
        [r'(&#299;)', r'ī'],
        [r'(&#333;)', r'ō'],
        [r'(&#363;)', r'ū'],
        [r'(&#462;)', r'ǎ'],
        [r'(&#770;)', r'̂'],
        [r'(&#772;)', r'̄'],
        [r'(&#8211;)', r'\\endash '],
        [r'(&#8212;)', r'\\emdash '],
        [r'(&#8216;)', r'\\lquote '],
        [r'(&#8217;)', r'\\rquote '],
        [r'(&#8220;)', r'\\ldblquote '],
        [r'(&#8221;)', r'\\rdblquote '],
        [r'(&#8226;)', r'•'],
        [r'(&#8230;)', r'...'],
        [r'(&#9632;)', r'■'],
        [r'(&#9658;)', r'►'],
        [r'(&#9791;)', r'☿'],
        [r'(&#9830;)', r'♦'],
        [r'(&#128521;)', r'😉'],
        [r'(&#128550;)', r'😦']
    ]
    special_substitutions = [
        [[r'<span style="text-decoration:underline;">', r'</span>'], [r'\\ul ', r'\\ul0 ']],
        [[r'<span style="color:#ffffff;">', r'</span>'], [r'', r'']],
        [[r'<span style="font-style:inherit;line-height:1.625;">', r'</span>'], [r'', r'']],
        [[r'<span style="font-size:15px;font-style:inherit;line-height:1.625;">', r'</span>'], [r'', r'']],
        [[r'<span style="line-height:15px;">', r'</span>'], [r'', r'']],
        [[r'<span style="color:#333333;font-style:normal;line-height:24px;">', r'</span>'], [r'', r'']],
        [[r'<span id=".+?">', r'</span>'], [r'', r'']]
        #[[r'<span.*?>', r'</span>'], [r'', r'']]  # <span> catch-all
    ]
    per_chapter_formatting = {
        1: {},
        2: {},
        3: {},
        4: {},
        5: {},
        6: {},
        7: {},
        8: {},
        9: {},
        10: {},
        11: {},
        12: {},
        13: {},
        14: {},
        15: {},
        16: {},
        17: {},
        18: {},
        19: {9: {'typeface': 3, 'font_size': 28, 'alignment': 'l', 'indent': 0, 'space_after': 360}},
        20: {},
        21: {},
        22: {},
        23: {},
        24: {},
        25: {},
        26: {},
        27: {},
        28: {},
        29: {},
        30: {},
        31: {}
    }


def intro_message():
    print('"Justice Shall Pervade"\n')
    return


def remove_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


def get_page(page_url, return_mode='tree'):
    def clamp(smallest, largest, n):
        return max(smallest, min(n, largest))
    
    legal_modes = ['tree', 'etree', 'string']
    page_request = request.Request(page_url, ''.encode('utf-8'), {'User-Agent': Constant.USER_AGENT_STRING})
    page_response = request.urlopen(page_request)
    if args.seconds is not None:
        time.sleep(random.randint(clamp(0, 4, abs(args.seconds) - 1), clamp(1, 6, abs(args.seconds) + 1)))
    page_string = page_response.read()
    page_response.close()
    if return_mode == 'tree' or return_mode not in legal_modes:
        return html.fromstring(page_string)
    elif return_mode == 'etree':
        return etree.fromstring(page_string)
    else:
        return page_string


def iri_to_uri(iri, encoding='utf-8'):
    """
    Sourced from https://gist.github.com/mnot/4576470; personally modified to support Python 3
    Takes a Unicode string that can contain an IRI and emits a URI.
    """
    scheme, authority, path, query, frag = urlparse.urlsplit(iri)
    scheme = scheme.encode(encoding)
    if ":" in authority:
        host, port = authority.split(':', 1)
        authority = host.encode('idna') + ':%s' % port
    else:
        authority = authority.encode(encoding)
    path = urlparse.quote(
        path.encode(encoding),
        safe='/;%[]=:$&()+,!?*@\'~'
    )
    query = urlparse.quote(
        query.encode(encoding),
        safe='/;%[]=:$&()+,!?*@\'~'
    )
    frag = urlparse.quote(
        frag.encode(encoding),
        safe='/;%[]=:$&()+,!?*@\'~'
    )
    return urlparse.urlunsplit((
        scheme.decode('utf-8'),
        authority.decode('utf-8'),
        path,
        query,
        frag
    ))


def get_index():
    index_tree = get_page(Constant.INDEX_URL)

    index_headings = index_tree.xpath('//*[@class="entry-content"]//strong')
    index_chapters = index_tree.xpath('//*[@class="entry-content"]//a')

    arc_number = 0
    heading_prefix = ''
    index = {}
    for heading in index_headings:
        heading_text = heading.text_content().strip()
        if heading_text != '':
            if heading_text[0] not in '1234567890':
                if heading_prefix != '':
                    arc_number += 1
                    index[arc_number] = {'arc': heading_prefix + heading_text}
                    heading_prefix = ''
                elif len(heading_text) == 1:
                    heading_prefix = heading_text
                elif '\n' in heading_text:
                    arc_number += 1
                    index[arc_number] = {'arc': heading_text.split('\n')[0].strip()}
                elif heading_text[0:2] != 'E.':
                    arc_number += 1
                    index[arc_number] = {'arc': heading_text}

    chapter_number = 0
    previous_arc_number = ''
    chapters = []
    for chapter in index_chapters:
        chapter_text = chapter.text_content().strip()
        chapter_url = chapter.attrib['href']
        if chapter_text != '':
            if chapter_text[0] in '1234567890E':
                if chapter_text[0] != 'E':
                    arc_number = int(chapter_text[0:chapter_text.find('.')])
                else:
                    arc_number = 31

                if arc_number == previous_arc_number:
                    chapter_number += 1
                else:
                    chapter_number = 1
                    previous_arc_number = arc_number

                chapters += chapter_text
                if arc_number == 31 and chapter_number == 2:  # This one's not in the index. Don't know why. Just isn't.
                    index[arc_number][chapter_number] = {}
                    index[arc_number][chapter_number]['chapter'] = 'E.2'
                    index[arc_number][chapter_number]['url'] = 'https://parahumans.wordpress.com/' \
                                                               '2013/11/05/teneral-e-2/'
                    chapter_number += 1

                index[arc_number][chapter_number] = {}
                if not args.faithful:
                    chapter_text_part = chapter_text.replace('(Donation ', '(')
                    index[arc_number][chapter_number]['chapter'] = re.sub(
                        r'Interlude.+? ',
                        r'Interlude; ',
                        chapter_text_part
                    )
                else:
                    index[arc_number][chapter_number]['chapter'] = chapter_text
                if chapter_url[0:4] == 'http':
                    index[arc_number][chapter_number]['url'] = iri_to_uri(chapter_url)
                else:
                    index[arc_number][chapter_number]['url'] = iri_to_uri('https://' + chapter_url)

    return index


def get_chapter(chapter_url, chapter_number, chapter_title, arc_number, arc_title, chapter_position):
    # Generate complete file header string
    def generate_file_header():
        file_header_string = ''
        file_header_string += RTF.file_header
        file_header_string += '\\margt%d' % Typesetting.page_margins['top']
        file_header_string += '\\margb%d' % Typesetting.page_margins['bottom']
        file_header_string += '\\margl%d' % Typesetting.page_margins['left']
        file_header_string += '\\margr%d' % Typesetting.page_margins['right']
        file_header_string += '\n{\\fonttbl '
        file_header_string += '{\\f0 %s;}' % Typesetting.font['primary']['typeface']
        file_header_string += '{\\f1 %s;}' % Typesetting.font['header']['typeface']
        file_header_string += '{\\f2 %s;}' % Typesetting.font['footer']['typeface']
        file_header_string += '{\\f3 %s;}' % Typesetting.font['chapter_title']['typeface']
        file_header_string += '{\\f4 %s;}' % Typesetting.font['chapter_subtitle']['typeface']
        file_header_string += '{\\f5 %s;}' % Typesetting.font['chapter_end']['typeface']
        file_header_string += '{\\f6 %s;}' % Typesetting.font['cover_title']['typeface']
        file_header_string += '{\\f7 %s;}' % Typesetting.font['cover_author']['typeface']
        file_header_string += '{\\f8 %s;}' % Typesetting.font['cover_other']['typeface']
        file_header_string += '}\n'

        return file_header_string

    # Generate cover page string
    def generate_cover_page():
        # Empty header + footer is a hack to "fix" a bug in AbiWord. Please do not remove.
        cover_string = ''
        cover_string += '{\\header\\pard\\par}\n'
        cover_string += '{\\footer\\pard\\par}\n'

        cover_string += '\\sectd'
        cover_string += '{\\pard\\sa0\\qc\\fs24\\line\\par}\n'
        cover_string += '{\\pard\\sa0\\qc\\f6\\fs%d\\b %s\\b0\\par}\n' % (  # Prints title
            Typesetting.font['cover_title']['size'],
            re.sub(r'(\(.*?\))', r'', arc_title.upper())
        )
        cover_string += '{\\pard\\sa0\\qc\\fs24%s\\par}\n' % ('\\line' * 5)  # Adds space

        # Adds cover art
        cover_image_file = open(RTF.cover_image_file, 'r')
        cover_image_lines = cover_image_file.readlines()
        cover_image_file.close()
        cover_string += '{\\pard\\qc'
        for line in cover_image_lines:
            cover_string += line
        cover_string += '\\par}\n'

        cover_string += '{\\pard\\sa0\\qc\\fs24%s\\par}\n' % ('\\line' * 5)  # Adds space
        cover_string += '{\\pard\\sa120\\qc\\f7\\fs%d\\b JOHN McCRAE\\b0\\par}\n' % (  # Prints author name
            Typesetting.font['cover_author']['size']
        )
        cover_string += '{\\pard\\sa0\\qc\\f7\\fs28\\b WILDBOW\\b0\\page\\par}\n'  # Prints author nickname

        # Prints inner cover
        inner_cover_file = open(RTF.inner_cover_file, 'r')
        inner_cover_lines = inner_cover_file.readlines()
        inner_cover_file.close()
        inner_cover_lines = [line.strip() for line in inner_cover_lines]
        for line in inner_cover_lines:
            #cover_string += '{\\pard\\qc\\f0\\fs24 %s\\par}\n' % line
            cover_string += '{\\pard\\qc\\f0\\fs24 %s\\par}\n' % line

        return cover_string

    # Convert HTML to RTF
    def rich_textify(input_string, typeface=0, font_size=0, alignment='j', indent=1, space_after=False):
        output_string = input_string.replace('\n', '')  # Removes newlines from HTML, which would mess up some regex's
        output_string_prefix = RTF.line_prefix
        output_string_suffix = RTF.line_suffix

        for substitution in RTF.special_substitutions:
            output_string = re.sub(
                r'%s(.*?)%s' % (substitution[0][0], substitution[0][1]),
                r'%s\1%s' % (substitution[1][0], substitution[1][1]),
                output_string
            )

        if '<span' in output_string:
            print('ERROR: unprocessed <span>: %s' % re.findall(r'(<span.*?>.*?</span>)', output_string))
            if args.verbose or args.debug:
                print('DEBUG: complete line: %s' % output_string)

        for substitution in RTF.substitutions:
            output_string = re.sub(substitution[0], substitution[1], output_string)
        for substitution in RTF.character_substitutions:
            output_string = re.sub(substitution[0], substitution[1], output_string)

        if re.sub(r'[^a-z]', r'', output_string.lower()) in ['lastchapter',
                                                             'nextchapter',
                                                             'lastchapternextchapter',
                                                             'nextchapterlastchapter',
                                                             'lastchapternextchapterline',
                                                             'nextchapterlastchapterline']:
            return ''

        for character_code in re.findall(r'&#(.+?);', output_string):
            print('ERROR: unprocessed character code encountered: %s' % character_code)
            if args.verbose or args.debug:
                print('DEBUG: complete line:' % output_string)

        output_string = ' ' * (output_string[0] != '\\') + output_string

        css = re.search(r'<p.+?style="(.+?)".*?>', input_string)
        if css is None:
            output_string_prefix += ('\\q%s' % alignment) + ('\\fi%d' % Typesetting.indent) * indent
        else:
            css_dict = {}
            for css_string in re.split(r';', css.group(1)):
                if css_string != '':
                    css_list = re.split(r':', css_string)
                    css_dict[css_list[0]] = css_list[1]
            if args.verbose or args.debug:
                print('DEBUG: %02d-%02d: css_dict = %s' % (arc_number, chapter_number, css_dict))
                print('    %s' % input_string)

            if 'text-align' in css_dict.keys():
                if css_dict['text-align'] == 'left':
                    output_string_prefix += '\\ql'
                elif css_dict['text-align'] == 'right':
                    output_string_prefix += '\\qr'
                else:
                    output_string_prefix += '\\qc'
            if 'padding-left' in css_dict.keys():
                output_string_prefix += '\\li%d\\ri%d' % (Typesetting.padding, Typesetting.padding)

        output_string_prefix += ('\\f%d' % typeface) * (typeface != 0) + ('\\fs%d' % font_size) * (font_size != 0) + \
                                ('\\sa%d' % space_after) * (space_after != 0)

        return output_string_prefix + output_string + output_string_suffix

    chapter_tree = get_page(chapter_url)  # Downloads chapter page
    chapter_lines = chapter_tree.xpath('//*[@class="entry-content"]//p')
    if not args.join:
        # If the program IS NOT set to download all chapters of an arc as a joined file, save them in the format:
        # "##-## Chapter Title.rtf"
        chapter_path = '%02d-%02d %s.rtf' % (arc_number, chapter_number, chapter_title)
        chapter_file = open(chapter_path, 'w')
        # Writes the file header; contains stuff like the margins and font table
        chapter_file.write(generate_file_header())
    else:
        # If the program IS set to download all chapters of an arc as a joined file, save them in the format:
        # "Arc ## - Arc Title.rtf"
        if arc_title[0] != 'E':  # Renames numbered arc files (e.g. "Arc 01..." instead of "Arc 1...") for sorting
            chapter_path = 'Arc %02d - %s.rtf' % (arc_number, arc_title.split(':')[1].strip())
        else:
            chapter_path = '%s.rtf' % arc_title.replace(': ', ' - ')
        if chapter_position == 1:
            remove_file(chapter_path)
        chapter_file = open(chapter_path, 'a')
        if chapter_position == 1:
            # If it's working on the first chapter of an arc, then it writes the file header
            chapter_file.write(generate_file_header())

    if chapter_position == 1:  # Cover page stuff
        chapter_file.write(generate_cover_page())

    # Splits the chapter title into parts for various processing
    chapter_title_parts = [part.strip() for part in re.split(r'\(|;|:|\)', chapter_title) if part != '']

    # Set headers to current chapter + arc; resets the footers for the new \sect(ion)
    chapter_file.write('{\\headerl\\pard\\ql\\f1\\fs%d\\line %s\\par}\n' % (
        Typesetting.font['header']['size'],
        arc_title.upper()
    ))
    if len(chapter_title_parts) == 1:
        chapter_file.write('{\\headerr\\pard\\qr\\f1\\fs%d\\line %s\\par}\n' % (Typesetting.font['header']['size'], (
            ('Chapter %s' % chapter_title_parts[0]).upper()
        )))
    elif len(chapter_title_parts) == 2:
        chapter_file.write('{\\headerr\\pard\\qr\\f1\\fs%d\\line %s\\par}\n' % (Typesetting.font['header']['size'], (
            ('%s (%s)' % (chapter_title_parts[0], chapter_title_parts[1])).upper()
        )))
    else:
        chapter_file.write('{\\headerr\\pard\\qr\\f1\\fs%d\\line %s\\par}\n' % (Typesetting.font['header']['size'], (
            ('%s (%s; %s)' % (
                chapter_title_parts[0],
                chapter_title_parts[1].replace('Donation ', ''),
                chapter_title_parts[2]
            )).upper()
        )))
    chapter_file.write('{\\headerf\\pard\\par}\n')
    chapter_file.write('{\\footerl\\pard\\ql\\f2\\fs%d\\line\\chpgn\\par}\n' % Typesetting.font['footer']['size'])
    chapter_file.write('{\\footerr\\pard\\qr\\f2\\fs%d\\line\\chpgn\\par}\n' % Typesetting.font['footer']['size'])
    chapter_file.write('{\\footerf\\pard\\par}\n')

    # Start new \sect(ion), print chapter heading
    chapter_file.write('\\sect\\sectd\n')
    chapter_file.write('{\\pard\\page\\par}\n')
    if len(chapter_title_parts) == 1:
        chapter_file.write('{\\pard\\sa480\\qc\\f3\\fs%d\\b %s\\b0\\par}\n' % (
            Typesetting.font['chapter_title']['size'],
            chapter_title_parts[0]
        ))
    else:
        chapter_file.write('{\\pard\\sa120\\qc\\f3\\fs%d\\b %s\\b0\\par}\n' % (
            Typesetting.font['chapter_title']['size'],
            chapter_title_parts[0]
        ))
        if len(chapter_title_parts) == 2:
            chapter_file.write('{\\pard\\sa480\\qc\\f3\\fs%d\\b %s\\b0\\par}\n' % (
                Typesetting.font['chapter_subtitle']['size'],
                chapter_title_parts[1]
            ))
        else:
            chapter_file.write('{\\pard\\sa480\\qc\\f3\\fs%d\\b %s; %s\\b0\\par}\n' % (
                Typesetting.font['chapter_subtitle']['size'],
                chapter_title_parts[1],
                chapter_title_parts[2]
            ))

    # Convert HTML to RTF
    for raw_line in chapter_lines:
        line = etree.tostring(raw_line).decode('utf-8').strip()
        if chapter_number not in RTF.per_chapter_formatting[arc_number].keys():
            rich_line = rich_textify(line)
        else:
            chapter_formatting = RTF.per_chapter_formatting[arc_number][chapter_number]
            rich_line = rich_textify(
                line,
                chapter_formatting['typeface'],
                chapter_formatting['font_size'],
                chapter_formatting['alignment'],
                chapter_formatting['indent'],
                chapter_formatting['space_after']
            )
        chapter_file.write(rich_line)

    if not args.join:
        chapter_file.write('{\\pard\\page\\par}\n}')
    elif chapter_position == 2:
        if arc_number != 31:
            arc_identifier = 'ARC ' + str(arc_number)
        else:
            arc_identifier = 'WORM'
        # "Empty header + footer is a hack to "fix" a bug in AbiWord. Please do not remove." Redux
        chapter_file.write('{\\header\\pard\\par}\n')
        chapter_file.write('{\\footer\\pard\\par}\n')
        chapter_file.write('\\sect\\sectd')
        chapter_file.write('{\\pard\\page\\par}\n')
        chapter_file.write('{\\pard\\qc\\f5\\b END OF %s\\b0\\par}\n}' % arc_identifier)

    chapter_file.close()

    return


def main():
    intro_message()

    if not args.debug:
        print('Downloading "Table of Contents"...')
    index = get_index()

    if not args.download and args.arc is None and args.chapter is None:
        print('\nTABLE OF CONTENTS:\n------------------')
        for arc_number in sorted(index.keys()):
            print('%d. %s' % (arc_number,
                              index[arc_number]['arc']))
            for chapter_number in sorted([key for key in index[arc_number].keys() if isinstance(key, int)]):
                print('    %d. %s ... %s' % (
                    chapter_number,
                    index[arc_number][chapter_number]['chapter'],
                    index[arc_number][chapter_number]['url']
                ))
    else:
        if not args.debug:
            print('Downloading chapter(s)...')
        all_arcs = sorted(index.keys())
        if args.arc is not None:
            selected_arcs = sorted([arc for arc in set(args.arc) if arc in all_arcs])
            if any(arc not in all_arcs for arc in set(args.arc)):
                print('ERROR: selected arcs %s do not exist; automatically deselected' %
                      sorted([arc for arc in set(args.arc) if arc not in all_arcs]))
            if selected_arcs == []:  # Even if your IDE tells you to change this line, DON'T DO IT.
                print('ERROR: no valid arcs selected; automatically exiting')
                return
        else:
            selected_arcs = all_arcs

        for arc_number in selected_arcs:
            all_chapters = sorted([key for key in index[arc_number].keys() if isinstance(key, int)])
            if args.chapter is not None and (len(selected_arcs) == 1 or arc_number == selected_arcs[0]):
                selected_chapters = sorted([chapter for chapter in set(args.chapter) if chapter in all_chapters])
                if any(chapter not in all_chapters for chapter in set(args.chapter)):
                    print('ERROR: selected chapters %s do not exist; automatically deselected' %
                          sorted([chapter for chapter in set(args.chapter) if chapter not in all_chapters]))
                if selected_chapters == []:  # Even if your IDE tells you to change this line, DON'T DO IT.
                    print('ERROR: no valid chapters selected; automatically skipping arc')
            else:
                selected_chapters = all_chapters

            for chapter_number in selected_chapters:
                if chapter_number in [key for key in index[arc_number].keys() if isinstance(key, int)]:
                    if not args.debug:
                        print('%02d-%02d. %s <%s>' % (
                            arc_number,
                            chapter_number,
                            index[arc_number][chapter_number]['chapter'],
                            index[arc_number][chapter_number]['url']
                        ))
                    if chapter_number == selected_chapters[0]:
                        chapter_position = 1
                    elif chapter_number == selected_chapters[len(selected_chapters) - 1]:
                        chapter_position = 2
                    else:
                        chapter_position = 0
                    get_chapter(
                        index[arc_number][chapter_number]['url'],
                        chapter_number,
                        index[arc_number][chapter_number]['chapter'],
                        arc_number,
                        index[arc_number]['arc'],
                        chapter_position
                    )

    return


if __name__ == '__main__':
    main()
    exit()
