#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div start_ul >;
use CGI::Carp 'fatalsToBrowser';
use URI::Escape 'uri_escape_utf8';
use NoteSys;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

binmode STDOUT, ':encoding(UTF-8)';

if (url_param('del') && defined param('decision')
 && param('decision') ne 'Yes') {
 print redirect(url);
 exit(0);
}

print header(-type => 'text/html; charset=UTF-8'), start_html(-title =>
 'Notes', -encoding => 'UTF-8', -style => {-src => 'notes.css'}, -head =>
 Link({-rel => 'icon', -type => 'text/png', -href => 'notes.png'}));
# Yes, specifying the encoding twice in this way is necessary so that CGI.pm
# will print it correctly and Safari & Firefox will interpret it correctly.
connectDB $dbfile;

sub wrapLine($;$) {
 my $str = shift;
 my $len = shift || 80;
 $str =~ s/\s+$//;
 my @lines = ();
 while (length $str > $len) {
  if (reverse(substr $str, 0, $len) =~ /\s+/) {
   push @lines, substr $str, 0, $len - $+[0], ''
  } else { push @lines, substr $str, 0, $len, '' }
  $str =~ s/^\s+//;
 }
 return (@lines, $str);
}

sub printNote($) {
 my $note = shift;
 print start_div({-class => 'noteBlock'}), b(escapeHTML($note->title)); 
 print ' ', span({-class => 'editDel'}, a({-href => url(-relative => 1) .
  '?edit=' . $note->idno}, 'Edit') . '&nbsp;' . a({-href => url(-relative => 1)
  . '?del=' . $note->idno}, 'Delete'));
 print pre(join "\n", map { escapeHTML $_ } map { wrapLine($_, 80) }
  split /\n/, $note->contents) if $note->contents ne '';
 print p({-class => 'tags'}, join ', ', map {
  a({-href => url(-relative => 1) . '?tag=' . uri_escape_utf8($_)},
   escapeHTML($_))
 } @{$note->tags});
 print p({-class => 'timestamp'}, 'Created:', $note->created);
 print p({-class => 'timestamp'}, 'Edited:', $note->edited)
  if $note->created ne $note->edited;
 print end_div;
}

sub parseTagList($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 map { $_ eq '' ? () : $_ } split /\s*,\s*/, $str;
}

print start_table({-border => 0, -align => 'center'}), start_Tr,
 start_td({-width => 500});
print p({-class => 'totals'}, countNotes, 'notes |', countTags, 'tags');
print p(a({-href => url(-relative => 1)}, 'All notes'), '|',
 a({-href => url(-relative => 1) . '?new'}, 'New note'));

if (defined url_param('edit')) {
 my $old = fetchNote url_param('edit');
 if (defined param('title')) {
  my $new = new Note idno => $old->idno, title => param('title'),
   contents => param('contents'), tags => [ parseTagList param('tags') ];
  updateNote($old, $new);
  print p('Note edited');
 } else {
  print start_form(-action => url(-relative => 1, -query => 1));
  print textfield('title', $old->title, 80, 255);
  print br, tt(textarea('contents', $old->contents, 10, 80)), br;
  print textfield('tags', join(', ', @{$old->tags}), 80, 255);
  print br, submit(-value => 'Submit'), '&nbsp;' x 20, reset, end_form;
 }
} elsif (defined url_param('tag')) {
 map { printNote(fetchNote $_) } getTaggedNoteIDs(url_param('tag'))
} elsif (defined url_param('new') || defined url_param('keywords')
 && url_param('keywords') =~ /\bnew\b/) {
 if (defined param('title')) {
  createNote(new Note title => param('title'), contents => param('contents'),
   tags => [ parseTagList param('tags') ]);
  print p('Note created');
 } else {
  print start_form(-action => url(-relative => 1, -query => 1));
  print textfield('title', '', 80, 255);
  print br, tt(textarea('contents', '', 10, 80)), br;
  print textfield('tags', '', 80, 255);
  print br, submit(-value => 'Submit'), end_form;
 }
} elsif (defined url_param('del')) {
 if (defined param('decision') && param('decision') eq 'Yes') {
  deleteNote(url_param('del'));
  print p('Note deleted');
 } else {
  print p('Are you sure you want to delete this note?');
  print start_form(-action => url(-relative => 1, -query => 1));
  print p(submit('decision', 'Yes'), '&nbsp;' x 20, submit('decision', 'No'));
  print end_form;
  printNote(fetchNote url_param('del'));
   # The 'edit' and/or 'delete' links should probably be omitted when
   # displaying the note here.
 }
} else { map { printNote(fetchNote $_) } getAllNoteIDs }

print p(a({-href => url(-relative => 1)}, 'All notes'), '|',
 a({-href => url(-relative => 1) . '?new'}, 'New note'));
print end_td, start_td({-class => 'tagList'});
print ul(map {
 li(a({-href => url(-relative => 1) . '?tag=' . uri_escape_utf8($_->[0])},
  escapeHTML($_->[0])), '(' . $_->[1] . ')');
} getTagsAndQtys);
print end_td, end_Tr, end_table, end_html;

END { $? ? abandonDB : disconnectDB }
