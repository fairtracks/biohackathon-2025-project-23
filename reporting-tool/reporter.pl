#!/usr/bin/env perl
use warnings;
use strict;
use feature 'say';

# Script to generate annotation report.
#
# We assume a metadata file and an AGAT report file are provided 
# Example files are in this repo.
# The metadata file is a placeholder. It will change when the actual metadata
# schema + data are ready
# 
# The AGAT file is not useable by the PDF renderer, we have to remove the header
# line first.
#
# Futher analysis files, e.g. Busco, are TODO
#
# Requirements to run this are:
# Perl
# duckdb - duckdb.org
# typst - typst.app

use v5.10.1;
no warnings 'experimental';

use Data::Dumper;
use List::Util 'uniq';
use Getopt::Long;
use JSON;

my ($meta_file, $gff_file, $busco_file);
GetOptions(
    'm=s' => \$meta_file,
    'g=s' => \$gff_file, # TODO
    'b=s' => \$busco_file, # TODO
) or die_usage();

sub die_usage {
    die "Usage: $0 [-m metadata_file] [-g gff_file] [-b busco_file]";
}

sub check_exit {
    return if $? == 0;
    if ($? == -1) {
        die "failed to execute: $!\n";
    }
    elsif ($? & 127) {
        die sprintf "child died with signal %d, %s coredump\n",
        ($? & 127),  ($? & 128) ? 'with' : 'without';
    }
    else {
        die sprintf "child exited with value %d\n", $? >> 8;
    }
}


die "Need metadata csv file" unless ($meta_file);

# Extract info from metadata csv file as JSON
my $json = qx(duckdb -json -c 'select bioproject_name, bioproject_id, refseq_accession, asm_name, release_date, organism_id, tol_prefix  from dtol_metadata limit 1;' $meta_file);
check_exit();

# Write to file report_main.json
open (my $fh, '>', 'report_main.json') or die "Error opening file report_main.json: $!";
print $fh $json;
close($fh) or die "Error closing file report_main.json: $!";

# TODO
# Prepare agat data - remove the header line, write out as agat.tsv

# Compile PDF
say qx(typst compile --input file=report_main.json report_template.typ report.pdf);
check_exit();

say "Build OK. PDF file is report.pdf";
