#!/usr/bin/python3
# Tool to automagically create ebooks from Wildbow's online source of Worm
# Zoetrophy 2016


"""
RTF documentation:
    https://www.safaribooksonline.com/library/view/rtf-pocket-guide/9781449302047/ch01.html
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
arg_parser.add_argument('-s', '--seconds', metavar='SECONDS', type=float,
                        help='time to wait after page load in seconds (automatically fuzzed)')
arg_parser.add_argument('-v', '--verbose', action='store_true',
                        help='display more verbose output for debugging')
arg_parser.add_argument('-x', '--debug', action='store_true',
                        help='display only errors and debugging messages')
args = arg_parser.parse_args()


class Constant:
    INDEX_URL = 'https://parahumans.wordpress.com/table-of-contents/'
    USER_AGENT_STRING = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.13' \
                        '(KHTML, like Gecko) Chrome/9.0.597.19 Safari/534.13'


class RTF:
    header = '{\\rtf1\\deflang1033\\plain\\fs28\\widowctrl\\hyphauto\\ftnbj' \
             '\\margt2160\\margb2160\\margl1440\\margr1440 ' \
             '{\\fonttbl {\\f0 Times New Roman;}{\\f1 Arial;}{\\f2 Courier;}}\n'
    prefix = '{\\pard\\sl360\\slmult1'
    suffix = '\\par}\n'
    indent = 360
    padding = 1080
    substitutions = [
        [r'(<em>)|(<i>)', r'\\i '],
        [r'(</em>)|(</i>)', r'\\i0 '],
        [r'(<strong>)|(<b>)', r'\\b '],
        [r'(</strong>)|(</b>)', r'\\b0 '],
        [r'((<br/>)|(<br />)|(<br>))', r'\\line\n'],
        [r'(<span style="text-decoration:underline;">)', r'\\ul '],
        [r'(</span>)', r'\\ul0 '],
        [r'((<p)|(</p)).*?(>)', r''],
        [r'((<a)|(</a)).*?(>)', r''],
        [r'(<del>).*?(</del>)', r''],
        [r'((<del)|(</del)|(<del/)).*?(>)', r''],
        [r'(<em/>)|(<i/>)', r''],
        [r'(<strong/>)|(<b/>)', r''],

        [r'(&#160;)', r'\\~'],
        [r'(&#199;)', r'Ç'],
        [r'(&#220;)', r'Ü'],
        [r'(&#233;)', r'é'],
        [r'(&#246;)', r'ö'],
        [r'(&#8211;)', r'\\endash '],
        [r'(&#8212;)', r'\\emdash '],
        [r'(&#8216;)', r'\\lquote '],
        [r'(&#8217;)', r'\\rquote '],
        [r'(&#8220;)', r'\\ldblquote '],
        [r'(&#8221;)', r'\\rdblquote '],
        [r'(&#8230;)', r'...'],
        [r'(&#9632;)', r'\\bullet']
    ]
    author_name = 'JOHN McCRAE'
    author_nickname = 'WILDBOW'


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
        host, port = authority.split(":", 1)
        authority = host.encode('idna') + ":%s" % port
    else:
        authority = authority.encode(encoding)
    path = urlparse.quote(
      path.encode(encoding),
      safe="/;%[]=:$&()+,!?*@'~"
    )
    query = urlparse.quote(
      query.encode(encoding),
      safe="/;%[]=:$&()+,!?*@'~"
    )
    frag = urlparse.quote(
      frag.encode(encoding),
      safe="/;%[]=:$&()+,!?*@'~"
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
                index[arc_number][chapter_number]['chapter'] = chapter_text
                if chapter_url[0:4] == 'http':
                    index[arc_number][chapter_number]['url'] = iri_to_uri(chapter_url)
                else:
                    index[arc_number][chapter_number]['url'] = iri_to_uri('https://' + chapter_url)

    return index


def get_chapter(chapter_url, chapter_number, chapter_title, arc_number, arc_title, chapter_position):
    def rich_textify(input_string):
        output_string = input_string

        for substitution in RTF.substitutions:
            output_string = re.sub(substitution[0], substitution[1], output_string)

        if re.sub(r'[^a-z]', r'', output_string.lower()) in ['lastchapter',
                                                             'nextchapter',
                                                             'lastchapternextchapter',
                                                             'nextchapterlastchapter',
                                                             'lastchapternextchapterline',
                                                             'nextchapterlastchapterline']:
            return ''

        for character_code in re.findall(r'&#(.+?);', output_string):
            print('ERROR: unknown character code encountered <%s>' % character_code)

        output_string = ' ' * (output_string[0] != '\\') + output_string

        css = re.search(r'style="(.+?)"', input_string)
        if css is None:
            output_string = RTF.prefix + '\\qj\\fi' + str(RTF.indent) + output_string + RTF.suffix
        else:
            css_dict = {}
            for css_string in re.split(r';', css.group(1)):
                if css_string != '':
                    css_list = re.split(r':', css_string)
                    css_dict[css_list[0]] = css_list[1]
            if args.verbose or args.debug:
                print('DEBUG: %02d-%02d: css_dict = %s' % (arc_number, chapter_number, css_dict))
                print('    %s' % input_string)

            output_string_prefix = RTF.prefix
            if 'text-align' in css_dict.keys():
                if css_dict['text-align'] == 'left':
                    output_string_prefix += '\\ql'
                elif css_dict['text-align'] == 'right':
                    output_string_prefix += '\\qr'
                else:
                    output_string_prefix += '\\qc'
            if 'padding-left' in css_dict.keys():
                output_string_prefix += '\\li%d\\ri%d' % (RTF.padding, RTF.padding)
            output_string = output_string_prefix + output_string + RTF.suffix

        return output_string

    chapter_tree = get_page(chapter_url)
    chapter_lines = chapter_tree.xpath('//*[@class="entry-content"]//p')
    if not args.join:
        chapter_path = '%02d-%02d %s.rtf' % (arc_number, chapter_number, chapter_title)
        chapter_file = open(chapter_path, 'w')
        chapter_file.write(RTF.header)
    else:
        chapter_path = '%s.rtf' % arc_title.replace(':', ' -')
        if chapter_position == 1:
            remove_file(chapter_path)
        chapter_file = open(chapter_path, 'a')
        if chapter_position == 1:
            chapter_file.write(RTF.header)

    if chapter_position == 1:  # Empty header/footers is a hack to "fix" a bug. Please do not remove.
        chapter_file.write('{\\headerl\\pard\\par}\n')
        chapter_file.write('{\\headerr\\pard\\par}\n')
        chapter_file.write('{\\headerf\\pard\\par}\n')
        chapter_file.write('{\\footerl\\pard\\par}\n')
        chapter_file.write('{\\footerr\\pard\\par}\n')
        chapter_file.write('{\\footerf\\pard\\par}\n')
        chapter_file.write('\\sectd')
        chapter_file.write('{\\pard\\sa180\\qc\\fs36\\par}\n')
        chapter_file.write('{\\pard\\sa180\\qc\\fs72\\f1\\b %s\\b0\\par}\n' % arc_title.upper())
        chapter_file.write('{\\pard\\sa180\\qc\\fs36\\f1%s\\par}\n' % ('\\line' * 20))
        chapter_file.write('{\\pard\\sa120\\qc\\fs42\\f1\\b %s\\b0\\par}\n' % RTF.author_name)
        chapter_file.write('{\\pard\\sa0\\qc\\fs28\\f1\\b %s\\b0\\par}\n' % RTF.author_nickname)
        chapter_file.write('{\\pard\\qc\\page\\fs24\\f1 This page left intentionally blank.\\par}\n')

    # Set headers to current chapter + arc
    chapter_file.write('{\\headerl\\pard\\ql\\fs28\\f1\\line\\line %s\\par}\n' % (
        arc_title.upper()
    ))
    chapter_file.write('{\\headerr\\pard\\qr\\fs28\\f1\\line\\line %s\\par}\n' % (
        ('Chapter %s' % chapter_title.upper()).upper()
    ))
    chapter_file.write('{\\headerf\\pard\\qc\\par}\n')
    chapter_file.write('{\\footerl\\pard\\ql\\fs28\\line\\chpgn\\par}\n')
    chapter_file.write('{\\footerr\\pard\\qr\\fs28\\line\\chpgn\\par}\n')
    chapter_file.write('{\\footerf\\pard\\qc\\fs28\\line\\par}\n')

    # Start new sect(ion), print chapter heading
    chapter_file.write('\\sect\\sectd\n')
    chapter_file.write('{\\pard\\page\\par}\n')
    chapter_title_parts = [part.strip() for part in re.split(r'\(|\)', chapter_title) if part != '']
    if not len(chapter_title_parts) > 1:
        chapter_file.write('{\\pard\\sa480\\qc\\fs56\\f2\\b %s\\b0\\par}\n' % chapter_title_parts[0])
    else:
        chapter_file.write('{\\pard\\sa120\\qc\\fs56\\f2\\b %s\\b0\\par}\n' % chapter_title_parts[0])
        chapter_file.write('{\\pard\\sa480\\qc\\fs28\\f2\\b %s\\b0\\par}\n' % chapter_title_parts[1])

    for raw_line in chapter_lines:
        line = etree.tostring(raw_line).decode('utf-8').strip()
        rich_line = rich_textify(line)
        chapter_file.write(rich_line)

    if not args.join:
        chapter_file.write('{\\pard\\page\\par}\n}')
    elif chapter_position == 2:
        if arc_number != 31:
            arc_identifier = 'ARC ' + str(arc_number)
        else:
            arc_identifier = 'WORM'
        chapter_file.write('{\\headerl\\pard\\par}\n')
        chapter_file.write('{\\headerr\\pard\\par}\n')
        chapter_file.write('{\\headerf\\pard\\par}\n')
        chapter_file.write('{\\footerl\\pard\\par}\n')
        chapter_file.write('{\\footerr\\pard\\par}\n')
        chapter_file.write('{\\footerf\\pard\\par}\n')
        chapter_file.write('\\sect\\sectd')
        chapter_file.write('{\\pard\\page\\par}\n')
        chapter_file.write('{\\pard\\qc\\f2\\b END OF %s\\b0\\par}\n}' % arc_identifier)

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
                          sorted([arc for arc in set(args.arc) if arc not in all_arcs]))
                if selected_chapters == []:
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