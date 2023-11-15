fn = "ab010130.16d";

if endsWith(fn, ".Z")
  % https://linux.die.net/man/1/uncompress
  stat = system("uncompress " + fn);
  assert(stat == 0, "failed to uncompress " + fn)
  [d, n] = fileparts(fn);
  fn = fullfile(d,n);
end

%% detect Hatanaka CRINEX
% currently, rinexread() doesn't handle CRINEX
% https://terras.gsi.go.jp/ja/crx2rnx.html
% download, extract "bin/crx2rnx" to this script directory
fid = fopen(fn);
line = fgetl(fid);
fclose(fid);

if contains(line, "CRINEX")
  stat = system("crx2rnx " + fn);
  assert(stat == 0, "failed to convert " + fn)
  s = extractBefore(fn, strlength(fn));
  fn = s + "o";
end


%% read RINEX
disp("read " + fn)
dat = rinexread(fn);