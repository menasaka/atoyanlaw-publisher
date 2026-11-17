<?php
/**
 * Atoyan Law Publisher - lets the Streamlit / GitHub publisher set the Yoast SEO title and
 * meta description of new blog posts through the REST API.
 *
 * WordPress ignores these fields from outside apps unless they are registered. Without this
 * snippet posts still publish; Yoast just falls back to its default title and description
 * (the publisher also saves the description as the post excerpt).
 *
 * The FAQ accordion, FAQ schema in <head> and the WP Rocket purge already work through the
 * "WP Content Autopilot Bridge" plugin that is active on atoyanlaw.com.
 *
 * Install ONE way:
 *  - Code Snippets plugin: Snippets -> Add New -> paste everything below "<?php" -> "Run everywhere" -> Save & Activate
 *  - or save this file as wp-content/mu-plugins/atoyanlaw-publisher-meta.php
 */

add_action( 'init', function () {
    foreach ( array( '_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_focuskw' ) as $key ) {
        register_post_meta( 'post', $key, array(
            'type'          => 'string',
            'single'        => true,
            'show_in_rest'  => true,
            'auth_callback' => function () {
                return current_user_can( 'edit_posts' );
            },
        ) );
    }
} );
