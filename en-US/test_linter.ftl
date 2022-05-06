-button-term = Test
button-test = Test
button-test-ref1 = Test { -button-term }
button-test-ref2 = Test { button-test }

short = Too short
wrong_character = Too short
button-quote = Wrong ' quote
button-quote1 = Wrong "" quote

button-with-var = This is a { $var }

button-test2 = {
    $var ->
        [t] Foo
       *[s] Bar
}

button-test2 =
    .tooltip = Test