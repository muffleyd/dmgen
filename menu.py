def menu(title, options=None, question=None, numbers=0, format=1, mod=1, entry=None):
    """Prints out the given input to a menu type format

       title is what is printed on the first (next) line

       options is a LIST/TUPLE or a STRING which will be printed, and the inputs that correspond with each option
       ex: [['Option 1',['o','op1']], ['Option 2',['O','op2']]]
         will yield
       'o'/'op1' - Option 1
       'O'/'op2' - Option 2
                                   ----  or  ----
       'Option 1, o/op1, Option 2, O/op2'
         will yield the same

       spaces may be placed liberally after each ',' in the string form, as the program will remove them
        when generating the menu
       ex: "o,o,p,p"  and "o,    o   , p    ,p" both give:
       'o' - o
       'p' - p
       as the resulting options

       using double commas: 'Option 1,,Option 2' creates a number as an option for each with the ',,', which will yield
       '1' - Option 1
       '2' - Option 2

       if numbers is set as 1, '1' is set as the first option for the first value,
        '2' is set as the first option for the second value, etc.

       placing a '-' before any of the options will make that option recieve a number as it's first possible input
       example:
           menu('Title','Option 1, -o/op1, Option 2, o2/op2, Option 3, -o3/op3') #note, numbers == 0 here
        or menu('Title','Option 1, -/o/op1, Option 2, o2/op2, Option 3, -o3/op3') #note, numbers == 0 here
        or menu('Title',[['Option 1', ['-','o','op1']], ['Option 2', ['o2','op2']], ['Option 3', ['-','o3','op3']]]) #note, numbers == 0 here

                   will print
           Title
           '1'/'o'/'op1' - Option 1
           'o2'/'op2' - Option 2
           '2'/'o3'/'op3' - Option 3

       placing a '-' before any of the options, and having numbers == 1 causes that option to not contain a number as the first choice
       example:
           menu('Title','Option 1, -o/op1, Option 2, o2/op2, Option 3, o3/op3', numbers=1)
                  will print
           Title
           'o'/'op1' - Option 1
           '1'/'o2'/'op2' - Option 2
           '2'/'o3'/'op3' - Option 3

       question is what is asked in the raw_input() call

       if format is set as 1 (default), all options are spaced out equally.
       example:
           'a'/'asdf'        - This option
           'anything'/'here' - That option


       example use of menu:
       a = menu('Main menu',[['Option 1',['o','op']],['Option 2',['O','op2']]],'Select an option',1)
                 -------- or -------
       a = menu('Main menu', 'Option 1,    o/op, Option 2,O/op2', 'Select an option', 1)
                               will yield:
           Main menu
           '1'/'o'/'op'  - Option 1
           '2'/'O'/'op2' - Option 2
           Select an option: (waits for user input here)

        if the user's input is not a possible option, it asks the question again
        the number option is what is returned (second option selected means 2 (type==int) is returned)"""
    if options is None:
        title, options = None, title

    ##### converts the string 'options' argument into the lists argument #####

    # example option (used throughout this section)
    # 'Option 1,     o/op, Option 2,, Option 3,  o/op3'
    # NoOptionException = 'Bad menu, you have a double comma, along with numbers flag on, means this option has nothing assigned to it!'
    if type(options) == str:
        options = [i.strip() for i in options.split(',')]
        options.append('')  # adds an extra option, if an odd number of args are sent (no comma after the last one)
        options = [[options[i], options[i + 1].split('/')]
                   for i in range(0, len(options) - 1, 2)]
        curNum = 1
        test = ['']
        for i in options:
            if not numbers and i[1] == test:  # no option given at all
                i[1][0] = i[0]
            elif numbers or i[1] == test or '-' in i[1]:
                if i[1] == test:
                    i[1] = [str(curNum)]
                elif '-' in i[1]:
                    if numbers:
                        del i[1][i[1].index('-')]
                        curNum -= 1
                    else:
                        i[1][i[1].index('-')] = str(curNum)
                else:
                    i[1].insert(0, str(curNum))
                curNum += 1

    # now is [['Option 1', ['o', 'op']], ['Option 2', ['-']], ['Option 3', ['o/op3']]] (ready for below)

    if question is None:
        question = 'Make a selection: '
    ask = ''
    max_len = 0
    current_num = 1
    all_options_str = []
    all_options = []

    for op in range(len(options)):
        all_options.append(options[op][1])
        all_options_str.append(''.join(["'%s'/" % j for j in options[op][1]])[:-1])
        if format:  # gets the max length of the options
            if max_len < len(all_options_str[-1]):
                max_len = len(all_options_str[-1])

    toP = ['%s%s - %s' % (all_options_str[i], ' ' * (max_len - len(all_options_str[i])),
                          options[i][0]) for i in range(len(options))]
    if title is not None:
        toP.insert(0, title)
    print('\n'.join(toP))
    while 1:
        if entry is not None:
            ask = entry
            print('%s%s' % (question, ask))
        else:
            ask = input(question)
        for get_op in range(len(all_options)):
            if ask in all_options[get_op]:
                return get_op + mod
        if entry:
            raise ValueError('data sent not valid (%s)' % entry)
