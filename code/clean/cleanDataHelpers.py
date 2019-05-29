import re
# used to check the subject[subjectScheme] payload to determine whether this is
# a dewey decimal subject
ddcNames = [
        "DDC",
        "ddc",
        "dewey",
        "DeweyDecimalClassification",
        "ddccode",
        "Dewey Classification"
            " (http://opac.bncf.firenze.sbn.it/opac/controller.jsp"
            "?action=dewey_browse&deweypath_cod=9)",
        "Dewey decimal Classification",
        "ddc-dbn",
        "eterms:DDC"
]

# Used to map the payload (subject["value"]) of a DDC-subject to the base classes
# of ANZSRC. Unhandled DDC classes:
#  ^03[^.] | Encyclopedias & books of facts
#  ^04[^.] | Unassigned (formerly Biographies)
#  ^05[^.] | Magazines, journals & serials
#  ^06[^.] | Associations, organizations & museums
#  ^08[^.] | Quotations
#  ^09[^.] | Manuscripts & rare books
#  ^35[^.] | Public administration & military science
#  ^39[^.] | Customs, etiquette, & folklore
#  ^50[^.] | Science (too specific, subcategories are partly handled)
#  ^64[^.] | Home & family management
#  ^79[^.] | Sports, games & entertainment
#  ^91[^.] | Geography & travel
#  ^92[^.] | Biography & genealogy

# ! order matters: first come first serve, rearranging might result in false
# positives

mappingDdc = [
        ["05 environmental sciences",
            re.compile(
                '^57[7-9].*'
                '|ddc 57[7-8]'
            )
        ],
        ["04 earth sciences",
            re.compile(
                '^55[^.]+.*'
                '|^56[^.]+.*'
                '|^ddc 55[^.]+.*'
                '|^ddc 56[^.]+.*'
                '|.*earth sciences and geology$'
                '|.*550\s*\|\s*geowissenschaften.*'
                '|^912$'
                '|geowissenschaften$'
            )
        ],
        ["11 medical and health sciences",
            re.compile(
                '^61[^.]+.*'
                '|^ddc 61[^.]+.*'
                '|^medizin und gesundheit'
                )
        ],
        ["06 biological sciences",
            re.compile(
                '^57[^.]+.*'
                '|^58[^.]+.*'
                '|^59[^.]+.*'
                '|^ddc 57[^.]+.*'
                '|^ddc 58[^.]+.*'
                '|^ddc 59[^.]+.*'
                '|.*naturwissenschaften::570.*'
                '|.*naturwissenschaften::580.*'
                '|.*naturwissenschaften::590.*'
                '|biology'
                )
        ],
        ["08 information and computing sciences",
            re.compile(
                '^00[^.]+.*'
                '|^01[^.]+.*'
                '|^02[^.]+.*'
                '|^ddc 00[^.]+.*'
                '|^ddc 01[^.]+.*'
                '|^ddc 02[^.]+.*'
                '|.*allgemeines, wissenschaft::000.*$'
                '|^bibliotheks- und informationswissenschaften$'
                )
        ],
        ["14 economics",
            re.compile(
                '^33[^.]+.*'
                '|^ddc 33[^.]+.*'
                '|^wirtschaft$'
                )
        ],
        ["09 engineering",
                re.compile(
                    '^62[^.]+.*'
                    '|^66[^.]+.*'
                    '|^67[^.]+.*'
                    '|^68[^.]+.*'
                    '|^ddc 62[^.]+.*'
                    '|^ddc 66[^.]+.*'
                    '|^ddc 67[^.]+.*'
                    '|^ddc 68[^.]+.*'
                    )
        ],
        ["02 physical science",
            re.compile(
                '^52[^.]+.*'
                '|^53[^.]+.*'
                '|^ddc 52[^.]+.*'
                '|^ddc 53[^.]+.*'
                '|.*530 \| physik.*'
                )
        ],
        ["21 history and archaeology",
                re.compile(
                    '^90[^.]+.*'
                    '|^93[^.]+.*'
                    '|^94[^.]+.*'
                    '|^95[^.]+.*'
                    '|^96[^.]+.*'
                    '|^97[^.]+.*'
                    '|^98[^.]+.*'
                    '|^99[^.]+.*'
                    '|^ddc 90[^.]+.*'
                    '|^ddc 93[^.]+.*'
                    '|^ddc 94[^.]+.*'
                    '|^ddc 95[^.]+.*'
                    '|^ddc 96[^.]+.*'
                    '|^ddc 97[^.]+.*'
                    '|^ddc 98[^.]+.*'
                    '|^ddc 99[^.]+.*'
                    '|^271.*'
                    )
        ],
        ["03 chemical science",
                re.compile(
                    '^54[^.]+.*'
                    '|^54[^.]+.*'
                    '|.*540 \| chemie.*'
                    )
        ],
        ["20 language, communication and culture",
                re.compile(
                    '^4\d+[^.]+.*'
                    '|^8\d+[^.-]+.*'
                    '|^306.*'
                    '|^ddc 4[^.]+.*'
                    '|^ddc 8[^.]+.*'
                    '|^ddc 306.*'
                    '|^8 language\. linguistics\. literature$'
                    '|^81 linguistics and languages'
                    '|.*dewey decimal classification::400 \| sprache, linguistik.*$'
                    '|.*dewey decimal classification::800 \| literatur, rhetorik, literaturwissenschaft.*$'
                    )
        ],
        ["16 studies in human society",
                re.compile(
                    '^30[^.]+.*'
                    '|^32[^.]+.*'
                    '|^36[^.]+.*'
                    '|^ddc 30[^.]+.*'
                    '|^ddc 32[^.]+.*'
                    '|^ddc 36[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330$'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::360.*'
                    '|^soziale probleme und sozialdienste; verbände$'
                    '|^0 social sciences'
                    '|^3 social sciences$'
                    '|^sozialwissenschaften$'
                    )
        ],
        ["07 agricultural and veterinary science",
                re.compile(
                    '^63[^.]+.*'
                    '|^ddc 63[^.]+.*'
                    '|^landwirtschaft und verwandte bereiche$'
                    '|.*technik::630.*'
                    )
        ],
        ["17 psychology and cognitive sciences",
                re.compile(
                    '^15[^.]+.*'
                    '|^ddc 15[^.]+.*'
                    '|^psychologie$'
                    )
        ],
        ["10 technology",
                re.compile(
                    '^60[^.]+.*'
                    '|^ddc 60[^.]+.*'
                    )
        ],
        ["13 education",
                re.compile(
                    '^37[^.]+.*'
                    '^507.*'
                    '|^ddc 37[^.]+.*'
                    '|^ddc 507.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::370.*'
                    )
        ],
        ["01 mathematical science",
                re.compile(
                    '^31\d+.*'
                    '|^51[^.]+.*'
                    '|^ddc 31[^.]+.*'
                    '|^ddc 51[^.]+.*'
                    '|.*510 \| mathematik.*'
                    )
        ],
        ["18 law and legal studies",
                re.compile(
                    '^34[^.]+.*'
                    '|^ddc 34[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::340.*'
                    '|^recht$'
                    )
        ],
        ["22 philosophy and religious studies",
                re.compile(
                    '^(1|2)\d+.*'
                    '|^507.*'
                    '|^ddc (1|2)[^.]+.*'
                    '|^ddc 507.*'

                    )
        ],
        ["19 studies in creative arts and writing",
                re.compile(
                    '^07[^.]+.*'
                    '|^70[^.]+.*'
                    '|^73[^.]+.*'
                    '|^74[^.]+.*'
                    '|^75[^.]+.*'
                    '|^76[^.]+.*'
                    '|^77[^.]+.*'
                    '|^78[^.]+.*'
                    '|^ddc 07[^.]+.*'
                    '|^ddc 70[^.]+.*'
                    '|^ddc 73[^.]+.*'
                    '|^ddc 74[^.]+.*'
                    '|^ddc 75[^.]+.*'
                    '|^ddc 76[^.]+.*'
                    '|^ddc 77[^.]+.*'
                    '|^ddc 78[^.]+.*'
                    )
        ],
        ["15 commerce, management, tourism and services",
                re.compile(
                    '^38[^.]+.*'
                    '|^65[^.].*'
                    '|^ddc 38[^.]+.*'
                    '|^ddc 65[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::380.*'
                    )
        ],
        ["12 built environment and design",
                re.compile(
                    '^69[^.*]'
                    '|^71[^.*]'
                    '|^72[^.*]'
                    '|^ddc 69[^.]+.*'
                    '|^ddc 71[^.]+.*'
                    '|^ddc 72[^.]+.*'
                    )
        ]
]

# ORDER MATTERS
mappingNarcis = [
        ["05 environmental sciences",
            re.compile(
                'http://www.narcis.nl/classfication/D224\d{2}'
            )
        ],
        ["04 earth sciences",
            re.compile(
                'http://www.narcis.nl/classfication/D15\d{3}'
            )
        ],
        ["11 medical and health sciences",
            re.compile(
                'http://www.narcis.nl/classfication/D2(3|4)\d{3}'
                )
        ],
        ["06 biological sciences",
            re.compile(
                'http://www.narcis.nl/classfication/D22\d{3}'
                )
        ],
        ["08 information and computing sciences",
            re.compile(
                'http://www.narcis.nl/classfication/D16\d{3}'
                )
        ],
        ["14 economics",
            re.compile(
                'http://www.narcis.nl/classfication/D70\d{3}'
                )
        ],
        ["09 engineering",
            re.compile(
                'http://www.narcis.nl/classfication/(D14310|D14220|D1443\d{1}|D1444\d{1}|D146\d{2})'
                )
        ],
        ["02 physical science",
            re.compile(
                'http://www.narcis.nl/classfication/(D12\d{3}|D17\d{3})'
                )
        ],
        ["21 history and archaeology",
                re.compile(
                'http://www.narcis.nl/classfication/(D34\d{3}|D37\d{3})'
                    )
        ],
        ["03 chemical science",
                re.compile(
                'http://www.narcis.nl/classfication/D13\d{3}'
                    )
        ],
        ["20 language, communication and culture",
                re.compile(
                'http://www.narcis.nl/classfication/(D36\d{3}|D63\d{3}|D66\d{3})'
                    )
        ],
        ["16 studies in human society",
                re.compile(
                'http://www.narcis.nl/classfication/(D6(0|1|8|9)\d{3}|D42\d{3})'
                    )
        ],
        ["07 agricultural and veterinary science",
                re.compile(
                'http://www.narcis.nl/classfication/(D18\d{3}|D26\d{3})'
                    )
        ],
        ["17 psychology and cognitive sciences",
                re.compile(
                'http://www.narcis.nl/classfication/(D51\d{3})'
                    )
        ],
        ["10 technology",
                re.compile(
                'http://www.narcis.nl/classfication/(E16\d{3}|D141\d{2}|D142(1|3|4)\d{1}|D143(1|2)\d{1}|D145\d{2}|D14(7|8|9)\d{2})'

                    )
        ],
        ["13 education",
                re.compile(
                'http://www.narcis.nl/classfication/(D52\d{3})'
                    )
        ],
        ["01 mathematical science",
                re.compile(
                'http://www.narcis.nl/classfication/(D11\d{3})'
                    )
        ],
        ["18 law and legal studies",
                re.compile(
                'http://www.narcis.nl/classfication/(D41\d{3})'
                    )
        ],
        ["22 philosophy and religious studies",
                re.compile(
                'http://www.narcis.nl/classfication/(D3(2|3)\d{3})'
                    )
        ],
        ["19 studies in creative arts and writing",
                re.compile(
                'http://www.narcis.nl/classfication/(D35(1|2|3)\d{2})'
                    )
        ],
        ["12 built environment and design",
                re.compile(
                'http://www.narcis.nl/classfication/(D355\d{2}|D147\d{2})'
                    )
        ]
]
# ORDER IS IRRELEVANT
mappingBk = [
        ["01 mathematical science", re.compile( '^31.*') ],
        ["02 physical science", re.compile( '^(33|39).*') ],
        ["03 chemical science", re.compile( '^35.*') ],
        ["04 earth sciences", re.compile( '^38.*') ],
        ["06 biological sciences", re.compile( '^42.*') ],
        ["07 agricultural and veterinary science", re.compile( '^(46|48).*') ],
        ["08 information and computing sciences", re.compile( '^54.*') ],
        ["09 engineering", re.compile( '^(51|52|53).*') ],
        ["10 technology", re.compile( '^(50|58).*') ],
        ["11 medical and health sciences", re.compile( '^44.*') ],
        ["12 built environment and design", re.compile( '^56.*') ],
        ["13 education", re.compile( '^(80|81).*') ],
        ["14 economics", re.compile( '^8(3|5).*') ],
        ["16 studies in human society", re.compile( '^(71|89).*') ],
        ["17 psychology and cognitive sciences", re.compile( '^77.*') ],
        ["18 law and legal studies", re.compile( '^86.*') ],
        ["19 studies in creative arts and writing", re.compile( '^(20|21|24).*') ],
        ["20 language, communication and culture", re.compile( '^(05|17|18|73).*') ],
        ["21 history and archaeology", re.compile( '^15.*') ],
        ["22 philosophy and religious studies", re.compile( '^(08|11).*') ]
]

# ORDER IS IRRELEVANT
mappingLinsearch = [
        ["01 mathematical science", re.compile( '^Mathematics$') ],
        ["02 physical science", re.compile( '^Physics$') ],
        ["03 chemical science", re.compile( '^Chemistry$') ],
        ["04 earth sciences", re.compile( '^Earth Science$')],
        ["06 biological sciences", re.compile( '^Biology$') ],
        ["07 agricultural and veterinary science", re.compile( '^Horticulture$') ],
        ["08 information and computing sciences", re.compile( '^Computer Science$') ],
        ["09 engineering", re.compile( '^Engineering$') ],
        ["12 built environment and design", re.compile( '^Architecture') ],
        ["13 education", re.compile( 'Educational Science') ],
        ["14 economics", re.compile( 'Economics') ],
        ["18 law and legal studies", re.compile( '^Law$') ],
        ["20 language, communication and culture", re.compile( '^Lingustics$') ],
        ["21 history and archaeology", re.compile( '^History$') ],
        ["22 philosophy and religious studies", re.compile( '^(Philosophy|Theology)$') ]
]

mappingBepress = [
        ["01 mathematical science",
            re.compile(

            )
        ],
        ["02 physical science",
            re.compile(

            )
        ],
        ["03 chemical science",
            re.compile(

            )
        ],
        ["04 earth sciences",
            re.compile(

            )
        ],
        ["05 environmental sciences",
            re.compile(

            )
        ],
        ["06 biological sciences",
            re.compile(

            )
        ],
        ["07 agricultural and veterinary science",
            re.compile(
             '^Agribusiness$'
            )
        ],
        ["08 information and computing sciences",
            re.compile(

            )
        ],
        ["09 engineering",
            re.compile(

            )
        ],
        ["10 technology",
            re.compile(

            )
        ],
        ["11 medical and health sciences",
            re.compile(

            )
        ],
        ["12 built environment and design",
            re.compile(
                '^Architectural Engineering$'
                '|^Architectural History and Criticism$'
                '|^Architectural Technology$'
                '|^Construction Engineering$'
                '|^Environmental Design$'
                '|^Historic Preservation and Conservation$'
                '|^Interior Architecture$'
                '|^Landscape Architecture$'
                '|^Other Architecture$'
             )
        ],
        ["13 education",
            re.compile(

            )
        ],
        ["14 economics",
            re.compile(
                '^Management Sciences and Quantitative Methods$'
            )
        ],
        ["15 commerce, management, tourism and services",
            re.compile(
             '^Business$'
             '|^Accounting$'
             '|^Advertising and Promotion Management$'
             '|^Arts Management$'
             '|^Arts Management: Music Business$'
             '|^Business Administration, Management, and Operations$'
             '|^Business Analytics$'
             '|^Business and Corporate Communications$'
             '|^Business Intelligence$'
             '|^E-Commerce$'
             '|^Entrepreneurial and Small Business Operations$'
             '|^Fashion Business$'
             '|^Finance and Financial Management$'
             '|^Hospitality Administration and Management$'
             '|^Hospitality Administration and Management: Food and Beverage Management$'
             '|^Hospitality Administration and Management: Gaming and Casino Operations Management$'
             '|^Human Resources Management$'
             '|^Human Resources Management: Benefits and Compensation $'
             '|^Human Resources Management: Performance Management$'
             '|^Human Resources Management: Training and Development$'
             '|^International Business$'
             '|^Labor Relations$'
             '|^Labor Relations: Collective Bargaining$'
             '|^Labor Relations: International and Comparative Labor Relations$'
             '|^Labor Relations: Unions$'
             '|^Management Information Systems$'
             '|^Marketing$'
             '|^Nonprofit Administration and Management$'
             '|^Operations and Supply Chain Management$'
             '|^Organizational Behavior and Theory$'
             '|^Portfolio and Security Analysis$'
             '|^Real Estate$'
             '|^Recreation Business$'
             '|^Sales and Merchandising$'
             '|^Sports Management$'
             '|^Strategic Management Policy$'
             '|^Technology and Innovation$'
             '|^Tourism and Travel$'
            )
        ],
        ["16 studies in human society",
            re.compile(
                 '^Feminist, Gender, and Sexuality Studies$'
                 '|^Lesbian, Gay, Bisexual, and Transgender Studies$'
                 '|^Women\'s Studies$'
                 '|^Other Feminist, Gender, and Sexuality Studies$'
                 '|^Race, Ethnicity and Post-Colonial Studies$'
                 '|^African American Studies$'
                 '|^Asian American Studies$'
                 '|^Chicana/o Studies$'
                 '|^Ethnic Studies$'
                 '|^Indigenous Studies$'
                 '|^Latina/o Studies$'
            )
        ],
        ["17 psychology and cognitive sciences",
            re.compile(

            )
        ],
        ["18 law and legal studies",
            re.compile(

            )
        ],
        ["19 studies in creative arts and writing",
            re.compile(
                 '^American Film Studies$'
                 '|^Art and Design$'
                 '|^Art and Materials Conservation$'
                 '|^Book and Paper$'
                 '|^Ceramic Arts$'
                 '|^Fashion Design$'
                 '|^Fiber, Textile, and Weaving Arts$'
                 '|^Furniture Design$'
                 '|^Game Design$'
                 '|^Glass Arts$'
                 '|^Graphic Design$'
                 '|^Illustration$'
                 '|^Industrial and Product Design$'
                 '|^Interactive Arts$'
                 '|^Interdisciplinary Arts and Media$'
                 '|^Interior Design$'
                 '|^Metal and Jewelry Arts$'
                 '|^Painting$'
                 '|^Printmaking$'
                 '|^Sculpture$'
                 '|^Art Practice$'
                 '|^Audio Arts and Acoustics$'
                 '|^Creative Writing$'
                 '|^Fiction$'
                 '|^Nonfiction$'
                 '|^Poetry$'
                 '|^Film and Media Studies$'
                 '|^Film Production$'
                 '|^Screenwriting$'
                 '|^Visual Studies$'
                 '|^Other Film and Media Studies$'
                 '|^Fine Arts$'
                 '|^Music$'
                 '|^Composition$'
                 '|^Ethnomusicology$'
                 '|^Music Education$'
                 '|^Music Practice$'
                 '|^Music Theory$'
                 '|^Musicology$'
                 '|^Music Pedagogy$'
                 '|^Music Performance$'
                 '|^Music Therapy$'
                 '|^Other Music$'
                 '|^Photography$'
                 '|^Radio$'
                 '|^Television$'
                 '|^Theatre and Performance Studies$'
                 '|^Acting$'
                 '|^Dance$'
                 '|^Dramatic Literature, Criticism and Theory$'
                 '|^Performance Studies$'
                 '|^Playwriting$'
                 '|^Theatre History$'
                 '|^Other Theatre and Performance Studies$'
            )
        ],
        ["20 language, communication and culture",
            re.compile(
                 '^African Languages and Societies$'
                 '|^Africana Studies$'
                 '|^American Studies$'
                 '|^American Literature$'
                 '|^American Material Culture$'
                 '|^American Popular Culture$'
                 '|^Appalachian Studies$'
                 '|^Australian Studies$'
                 '|^Basque Studies$'
                 '|^Celtic Studies$'
                 '|^Classics$'
                 '|^Byzantine and Modern Greek$'
                 '|^Classical Literature and Philology$'
                 '|^Indo-European Linguistics and Philology$'
                 '|^Comparative Literature$'
                 '|^Translation Studies$'
                 '|^Dutch Studies$'
                 '|^East Asian Languages and Societies$'
                 '|^Chinese Studies$'
                 '|^Japanese Studies$'
                 '|^Korean Studies$'
                 '|^English Language and Literature$'
                 '|^Children\'s and Young Adult Literature$'
                 '|^Literature in English, Anglophone outside British Isles and North America$'
                 '|^Literature in English, British Isles$'
                 '|^Literature in English, North America$'
                 '|^Literature in English, North America, Ethnic and Cultural Minority$'
                 '|^Other English Language and Literature$'
                 '|^European Languages and Societies$'
                 '|^French and Francophone Language and Literature$'
                 '|^French and Francophone Literature$'
                 '|^French Linguistics$'
                 '|^Other French and Francophone Language and Literature$'
                 '|^German Language and Literature$'
                 '|^German Linguistics$'
                 '|^German Literature$'
                 '|^Other German Language and Literature$'
                 '|^Italian Language and Literature$'
                 '|^Italian Linguistics$'
                 '|^Italian Literature$'
                 '|^Other Italian Language and Literature$'
                 '|^Jewish Studies$'
                 '|^Yiddish Language and Literature$'
                 '|^Language Interpretation and Translation$'
                 '|^Latin American Languages and Societies$'
                 '|^Caribbean Languages and Societies$'
                 '|^Modern Languages$'
                 '|^Modern Literature$'
                 '|^Near Eastern Languages and Societies$'
                 '|^Pacific Islands Languages and Societies$'
                 '|^Hawaiian Studies$'
                 '|^Melanesian Studies$'
                 '|^Micronesian Studies$'
                 '|^Polynesian Studies$'
                 '|^Reading and Language$'
                 '|^Scandinavian Studies$'
                 '|^Sign Languages$'
                 '|^American Sign Language$'
                 '|^Slavic Languages and Societies$'
                 '|^Russian Linguistics$'
                 '|^Russian Literature$'
                 '|^South and Southeast Asian Languages and Societies$'
                 '|^Spanish and Portuguese Language and Literature$'
                 '|^Latin American Literature$'
                 '|^Portuguese Literature$'
                 '|^Spanish Linguistics$'
                 '|^Spanish Literature$'
                 '|^Other Spanish and Portuguese Language and Literature$'
            )
        ],
        ["21 history and archaeology",
            re.compile(
                 '^Ancient History, Greek and Roman through Late Antiquity$'
                 '|^Classical Archaeology and Art History$'
                 '|^History$'
                 '|^African History$'
                 '|^Asian History$'
                 '|^Canadian History$'
                 '|^Cultural History$'
                 '|^Diplomatic History$'
                 '|^European History$'
                 '|^Genealogy$'
                 '|^History of Gender$'
                 '|^History of the Pacific Islands$'
                 '|^History of Religion$'
                 '|^History of Science, Technology, and Medicine$'
                 '|^Holocaust and Genocide Studies$'
                 '|^Intellectual History$'
                 '|^Islamic World and Near East History$'
                 '|^Labor History$'
                 '|^Latin American History$'
                 '|^Legal$'
                 '|^Medieval History$'
                 '|^Military History$'
                 '|^Oral History$'
                 '|^Political History$'
                 '|^Public History$'
                 '|^Social History$'
                 '|^United States History$'
                 '|^Women\'s History$'
                 '|^Other History$'
                 '|^Medieval Studies$'

            )
        ],
        ["22 philosophy and religious studies",
            re.compile(
                 '^Ancient Philosophy$'
                 '|^Philosophy$'
                 '|^Applied Ethics$'
                 '|^Comparative Philosophy$'
                 '|^Continental Philosophy$'
                 '|^Epistemology$'
                 '|^Esthetics$'
                 '|^Ethics and Political Philosophy$'
                 '|^Feminist Philosophy$'
                 '|^History of Philosophy$'
                 '|^Logic and Foundations of Mathematics$'
                 '|^Metaphysics$'
                 '|^Philosophy of Language$'
                 '|^Philosophy of Mind$'
                 '|^Philosophy of Science$'
                 '|^Other Philosophy$'
                 '|^Religion$'
                 '|^Biblical Studies$'
                 '|^Buddhist Studies$'
                 '|^Catholic Studies$'
                 '|^Christianity$'
                 '|^Christian Denominations and Sects$'
                 '|^Comparative Methodologies and Theories$'
                 '|^Ethics in Religion$'
                 '|^Hindu Studies$'
                 '|^History of Christianity$'
                 '|^History of Religions of Eastern Origins$'
                 '|^History of Religions of Western Origin$'
                 '|^Islamic Studies$'
                 '|^Liturgy and Worship$'
                 '|^Missions and World Christianity$'
                 '|^Mormon Studies$'
                 '|^New Religious Movements$'
                 '|^Practical Theology$'
                 '|^Religious Education$'
                 '|^Religious Thought, Theology and Philosophy of Religion$'
                 '|^Other Religion$'
            )
        ]
]
