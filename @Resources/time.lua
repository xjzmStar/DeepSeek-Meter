-- DeepSeek-Meter: read state.txt and set Rainmeter variables
-- Format: HH|MM|SS|datestr|peak_flag|cd_min|cd_sec|balance|alert|phase_text

function Initialize()
  stateFile = SKIN:MakePathAbsolute("@Resources\\state.txt")
end

function Update()
  local f = io.open(stateFile, "r")
  if not f then return end
  
  -- Read entire file
  local line = f:read("*l")
  f:close()
  
  -- Skip if empty or incomplete
  if not line or line == "" then return end
  
  -- Split by pipe
  local p = {}
  for part in string.gmatch(line, "([^|]+)") do
    table.insert(p, part)
  end
  
  -- Need at least 9 fields
  if #p < 9 then return end

  -- Set variables only if all fields are valid
  SKIN:Bang("!SetVariable", "Hour", p[1])
  SKIN:Bang("!SetVariable", "Min", p[2])
  SKIN:Bang("!SetVariable", "Sec", p[3])
  SKIN:Bang("!SetVariable", "DateStr", p[4])
  SKIN:Bang("!SetVariable", "IsPeak", p[5])
  SKIN:Bang("!SetVariable", "CdMin", p[6])
  SKIN:Bang("!SetVariable", "CdSec", p[7])
  SKIN:Bang("!SetVariable", "PhaseText", p[10] or p[9])

  -- Parse balance: "123.45|OK" or "12.34|ALERT" or "ERR|ERR"
  local balVal, balAlert = p[8]:match("^(.-)|(.+)$")
  if not balVal then balVal = p[8]; balAlert = "OK" end
  SKIN:Bang("!SetVariable", "BalanceRaw", balVal)
  SKIN:Bang("!SetVariable", "IsAlert", balAlert == "ALERT" and "1" or "0")
end
