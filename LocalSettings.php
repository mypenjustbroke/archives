<?php
if ( !defined( 'MEDIAWIKI' ) ) { exit; }

$wgSitename = "SimDemocracy Archives";
$wgMetaNamespace = "SimDemocracy_Archives";

$wgScriptPath = "";
$wgArticlePath = "/wiki/$1";
$wgUsePathInfo = true;
$wgServer = "http://localhost:8080";

$wgEnableUploads = false;
$wgUseInstantCommons = false;

$wgDBtype = "mysql";
$wgDBserver = "db";
$wgDBname = "my_wiki";
$wgDBuser = "wikiuser";
$wgDBpassword = "wikipass";
$wgDBTableOptions = "ENGINE=InnoDB, DEFAULT CHARSET=binary";

$wgSecretKey = "buildtime-only-not-public-1f7a3e9c2b4d6a8e0f1c3a5b7d9e1f3a";
$wgUpgradeKey = "buildtime-only-not-public-2e8b4f0d3c5a7b9e1d3f5a7c9b1d3e5a";

$wgLanguageCode = "en-GB";
$wgDefaultSkin = "vector";

# --- Read-only public mode ---
# CLI maintenance scripts (importDump, rebuildall) bypass these gates,
# so this is safe for the import phase.
$wgGroupPermissions['*']['edit']            = false;
$wgGroupPermissions['*']['createaccount']   = false;
$wgGroupPermissions['*']['createpage']      = false;
$wgGroupPermissions['*']['createtalk']      = false;
$wgGroupPermissions['*']['writeapi']        = false;
$wgGroupPermissions['*']['upload']          = false;
$wgGroupPermissions['*']['move']            = false;
$wgGroupPermissions['user']['edit']         = false;
$wgGroupPermissions['user']['createaccount']= false;
$wgGroupPermissions['user']['createpage']   = false;
$wgGroupPermissions['user']['upload']       = false;

$wgRightsPage = "";
$wgRightsUrl  = "";
$wgRightsText = "Snapshot of the SimDemocracy Archives, 2026-05-05.";
$wgRightsIcon = "";

# Suppress diagnostics in rendered HTML
$wgShowExceptionDetails = false;
$wgShowDBErrorBacktrace = false;
$wgShowSQLErrors        = false;
