/**
 * Test suite for navigation functionality
 * 
 * Generated from QA-AI exploration session
 * Base URL: https://defi.space
 * Generated: 2025-06-11T11:49:49.527980
 */

describe('navigation_tests', () => {
  beforeEach(() => {
    cy.visit('https://defi.space');
  });

  
  it('test_home_navigation_happy_path', () => {
    // Verify home navigation works correctly
    // User Story: As a user, I want to home navigation successfully
    // Priority: medium
    
    // Click link: HOME
    cy.get('[data-testid="home"], [data-test="home"], [aria-label="HOME"], a:has-text("HOME"), text="HOME"').click({ timeout: 5701 });

  });

  
  it('test_navigation_to_defi.space_happy_path', () => {
    // Verify navigation to defi.space works correctly
    // User Story: As a user, I want to navigation to defi.space successfully
    // Priority: medium
    
    // Click link: DEFI.SPACE
    cy.get('[data-testid="defi-space"], [data-test="defi-space"], [aria-label="DEFI.SPACE"], a:has-text("DEFI.SPACE"), text="DEFI.SPACE"').click({ timeout: 5689 });

  });

  
  it('test_navigation_to_sessions_happy_path', () => {
    // Verify navigation to sessions works correctly
    // User Story: As a user, I want to navigation to sessions successfully
    // Priority: medium
    
    // Click link: SESSIONS
    cy.get('[data-testid="sessions"], [data-test="sessions"], [aria-label="SESSIONS"], a:has-text("SESSIONS"), text="SESSIONS"').click({ timeout: 5683 });

  });

  
  it('test_navigation_to_claim_happy_path', () => {
    // Verify navigation to claim works correctly
    // User Story: As a user, I want to navigation to claim successfully
    // Priority: medium
    
    // Click link: CLAIM
    cy.get('[data-testid="claim"], [data-test="claim"], [aria-label="CLAIM"], a:has-text("CLAIM"), text="CLAIM"').click({ timeout: 5679 });

  });

  
  it('test_navigation_to_claim_dst_happy_path', () => {
    // Verify navigation to claim dst works correctly
    // User Story: As a user, I want to navigation to claim dst successfully
    // Priority: medium
    
    // Click link: CLAIM DST
    cy.get('[data-testid="claim-dst"], [data-test="claim-dst"], [aria-label="CLAIM DST"], a:has-text("CLAIM DST"), text="CLAIM DST"').click({ timeout: 5958 });

  });

  
  it('test_navigation_to_docs_happy_path', () => {
    // Verify navigation to docs works correctly
    // User Story: As a user, I want to navigation to docs successfully
    // Priority: medium
    
    // Click link: docs
    cy.get('[data-testid="docs"], [data-test="docs"], [aria-label="docs"], a:has-text("docs"), text="docs"').click({ timeout: 5744 });

  });

  
  it('test_navigation_to_follow_happy_path', () => {
    // Verify navigation to follow works correctly
    // User Story: As a user, I want to navigation to follow successfully
    // Priority: medium
    
    // Click link: FOLLOW
    cy.get('[data-testid="follow"], [data-test="follow"], [aria-label="FOLLOW"], a:has-text("FOLLOW"), text="FOLLOW"').click({ timeout: 5905 });

  });

  
  it('test_navigation_to_github_happy_path', () => {
    // Verify navigation to github works correctly
    // User Story: As a user, I want to navigation to github successfully
    // Priority: medium
    
    // Click link: github
    cy.get('[data-testid="github"], [data-test="github"], [aria-label="github"], a:has-text("github"), text="github"').click({ timeout: 5719 });

  });

  
  it('test_navigation_to_x_happy_path', () => {
    // Verify navigation to x works correctly
    // User Story: As a user, I want to navigation to x successfully
    // Priority: medium
    
    // Click link: x
    cy.get('[data-testid="x"], [data-test="x"], [aria-label="x"], a:has-text("x"), text="x"').click({ timeout: 5707 });

  });

  
  it('test_navigation_to_discord_happy_path', () => {
    // Verify navigation to discord works correctly
    // User Story: As a user, I want to navigation to discord successfully
    // Priority: medium
    
    // Click link: discord
    cy.get('[data-testid="discord"], [data-test="discord"], [aria-label="discord"], a:has-text("discord"), text="discord"').click({ timeout: 5722 });

  });

});
