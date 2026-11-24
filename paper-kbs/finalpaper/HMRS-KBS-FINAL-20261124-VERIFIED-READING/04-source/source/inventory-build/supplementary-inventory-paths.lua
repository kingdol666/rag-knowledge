-- Keep inline code readable without changing its text. Pandoc's default
-- inline-code \texttt{} never breaks, so a long path or tool name such as
-- kb_project_update(show_version=True) can overrun the right margin. Code
-- without a space or a pipe goes through \path|...| (xurl allows line
-- breaks inside it); anything else keeps the default.
function Code(el)
  if el.text:find(' ', 1, true) or el.text:find('|', 1, true) then
    return nil
  end
  return pandoc.RawInline('latex', '\\path|' .. el.text .. '|')
end
