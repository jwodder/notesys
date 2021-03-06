#!/usr/bin/perl -wl -CO
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div start_ul >;
use CGI::Carp 'fatalsToBrowser';
use Regexp::Common 'URI';
use URI::Escape 'uri_escape_utf8';
use NoteSys;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

# This whole 'mode' system may be overkill, but it allows the code for
# switching between modes to be neatly encapsulated into one place from which
# it can be easily modified, e.g., to use Apache URL rewriting instead of query
# strings.
use constant {MODE_INTARG => 1, MODE_TEXTARG => 2};
my %modeHash = (new => 0, back => 0, edit => MODE_INTARG, del => MODE_INTARG,
 tag => MODE_TEXTARG);
my $mode = url_param('mode');
my $modeArg = url_param('arg');
$mode = 'all' if !defined $mode || !exists $modeHash{$mode}
 || $modeHash{$mode} != 0 && (!defined $modeArg || $modeArg eq ''
 || $modeHash{$mode} & MODE_INTARG && $modeArg !~ /^\d+$/);

sub modeLink($;$) {
 my($mode, $arg) = @_;
 return url if $mode eq 'all';
 my $url = url . "?mode=$mode";
 if (defined $arg) { return $url . '&arg=' . uri_escape_utf8($arg) }
 else { return $url }
}

if ($mode eq 'back' || $mode eq 'del' && defined param('decision')
 && param('decision') ne 'Yes') {
 my $last = cookie('lastTag');
 print redirect(defined $last && $last ne '' ? modeLink('tag', $last)
  : modeLink 'all');
 exit(0);
}

my @cookies = ();
if ($mode eq 'all') {
 @cookies = (-cookie => cookie(-name => 'lastTag', -value => ''))
} elsif ($mode eq 'tag') {
 @cookies = (-cookie => cookie(-name => 'lastTag', -value => $modeArg))
}

print header(-type => 'text/html; charset=UTF-8', @cookies);
print start_html(-title => $mode eq 'tag' ? "Notes \x{2014} $modeArg" : 'Notes',
 -encoding => 'UTF-8',
 # Yes, specifying the encoding twice is necessary so that CGI.pm will send the
 # correct headers and so that the in-document charset information agrees with
 # said headers.
 -declare_xml => 1,
 -style => {-src => 'notes.css'},
 -head => Link({-rel => 'icon', -type => 'text/png', -href => 'notes.png'}));

connectDB $dbfile;

sub wrapLines($;$) {
 my $str = shift;
 my $len = shift || 80;
 $str =~ s/\s+\z//;
 map {
  s/\s+\z//;
  if ($_ eq '') { ('') }
  else {
   my @lines = ();
   while (length > $len && /\s+/) {
    if (reverse (substr $_, 0, $len + 1) =~ /\s+/) {
     # Adding one to the length causes a space immediately after the first $len
     # characters to be taken into account.
     push @lines, substr $_, 0, $len + 1 - $+[0], ''
    } else { /\s+/ && push(@lines, substr $_, 0, $-[0], '') }
    s/^\s+//;
   }
   $_ eq '' ? @lines : (@lines, $_);
  }
 } split /\n/, $str;
}

sub printNote($) {
 my $note = shift;
 return if !defined $note;
 print start_div({-class => 'noteBlock'}), b(escapeHTML($note->title)); 
 print ' ', span({-class => 'editDel'}, a({-href => modeLink('edit',
  $note->idno)}, 'Edit') . '&nbsp;' . a({-href => modeLink('del',
  $note->idno)}, 'Delete'));
 print pre(join "\n", map {
   s/\G(.*?)($RE{URI})|\G(.+)$
    /defined $1 ? escapeHTML($1) . a({-href => $2}, escapeHTML $2)
		: escapeHTML $3  # CGI.pm escapes HREF attributes automatically.
    /gex;
   $_;
  } wrapLines($note->contents, 80)) if $note->contents ne '';
 print p({-class => 'tags'}, join ', ', map {
  a({-href => modeLink('tag', $_)}, escapeHTML($_))
 } $note->tagList);
 print p({-class => 'timestamp'}, 'Created:', $note->created);
 print p({-class => 'timestamp'}, 'Last edited:', $note->edited)
  if $note->created ne $note->edited;
 print end_div;
}

sub parseTagList($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 map { $_ eq '' ? () : $_ } split /\s*,\s*/, $str;
 ### Why not `grep { $_ ne '' } ...` ?
}

print start_table({-border => 0, -align => 'center'}), start_Tr,
 start_td({-width => 500});
print p(a({-href => modeLink 'all'}, 'All notes'), '|',
 a({-href => modeLink 'new'}, 'New note'));

if ($mode eq 'edit') {
 my $old = fetchNote $modeArg;
 if (!defined $old) {
  print p("There is no note #$modeArg....");
  print p(a({-href => modeLink 'back'}, 'Back'));
 } elsif (defined param('title')) {
  my $new = new Note idno => $old->idno, title => param('title'),
   contents => param('contents'), tags => [ parseTagList param('tags') ];
  updateNote($old, $new);
  print p('Note edited'), p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  print start_form(-action => modeLink($mode, $modeArg));
  print textfield('title', $old->title, 80, 255);
  print br, tt(textarea('contents', $old->contents, 10, 80)), br;
  print textfield('tags', join(', ', $old->tagList), 80);
  print br, submit(-value => 'Save'), '&nbsp;' x 20, reset, '&nbsp;' x 20,
   a({-href => modeLink 'back'}, 'Back'), end_form;
 }
} elsif ($mode eq 'tag') {
 my @notes = getTaggedNoteIDs $modeArg;
 if (@notes) { map { printNote(fetchNote $_) } @notes }
 else { print p("There's nothing here.") }
} elsif ($mode eq 'new') {
 if (defined param('title')) {
  createNote(new Note title => param('title'), contents => param('contents'),
   tags => [ parseTagList param('tags') ]);
  print p('Note created'), p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  print start_form(-action => modeLink 'new');
  print textfield('title', '', 80, 255);
  print br, tt(textarea('contents', '', 10, 80)), br;
  print textfield('tags', '', 80);
  print br, submit(-value => 'Save'), '&nbsp;' x 20, a({-href =>
   modeLink 'back'}, 'Back'), end_form;
 }
} elsif ($mode eq 'del') {
 if (defined param('decision') && param('decision') eq 'Yes') {
  deleteNote $modeArg;
  print p('Note deleted'), p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  my $delee = fetchNote $modeArg;
  if (!defined $delee) {
   print p("There is no note #$modeArg....");
   print p(a({-href => modeLink 'back'}, 'Back'));
  } else {
   print p('Are you sure you want to delete this note?');
   print start_form(-action => modeLink($mode, $modeArg));
   print p(submit('decision', 'Yes'), '&nbsp;' x 20, submit('decision', 'No'));
   print end_form;
   printNote $delee;
    # The 'edit' and/or 'delete' links should probably be omitted when
    # displaying the note here.
  }
 }
} else {
 my @notes = getAllNoteIDs;
 if (@notes) { map { printNote(fetchNote $_) } @notes }
 else { print p("There's nothing here.") }
}

print p(a({-href => modeLink 'all'}, 'All notes'), '|',
 a({-href => modeLink 'new'}, 'New note'));

print end_td, start_td({-class => 'tagList'});

my($notes, $tags) = (countNotes, countTags);
print p({-class => 'totals'}, $notes, $notes == 1 ? 'note' : 'notes', '|',
 $tags, $tags == 1 ? 'tag' : 'tags');

print ul(map {
 li(a({-href => modeLink('tag', $_->[0])}, escapeHTML($_->[0])),
  '(' . $_->[1] . ')');
} getTagsAndQtys);

print end_td, end_Tr, end_table, end_html;

END { $? ? abandonDB : disconnectDB }
