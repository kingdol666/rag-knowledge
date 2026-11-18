-- Keep archived artifact paths readable without changing their text.
-- Pandoc's default inline-code \texttt{} does not wrap long paths.
function Code(el)
  if el.text:find('/', 1, true) and not el.text:find('|', 1, true) then
    return pandoc.RawInline('latex', '\\path|' .. el.text .. '|')
  end
end
