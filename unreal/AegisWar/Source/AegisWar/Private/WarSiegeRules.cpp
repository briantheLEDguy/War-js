#include "WarSiegeRules.h"

bool WarSiege::ValidCapacity(int32 N) { return N == 6 || N == 12 || N == 18; }
float WarSiege::HealthScale(int32 N) { return ValidCapacity(N) ? N / 6.f : 0.f; }
int32 WarSiege::Reinforcements(int32 N, bool Sabotaged)
{ return ValidCapacity(N) ? (Sabotaged ? N / 6 : N / 3) : 0; }
float WarSiege::ParticipationRate(int32 N, bool Escort)
{ return N <= 0 ? 0.f : FMath::Min(Escort ? 1.5f : 2.5f, 1.f + .25f * (N - 1)); }
int32 WarSiege::FinalObjective(int32 Stage) { return Stage == 0 ? 3 : Stage == 1 ? 2 : 0; }
bool WarSiege::IsEscort(const FWarSiegeState& S) { return S.Stage == 0 && (S.Objective == 1 || S.Objective == 2); }
uint16 WarSiege::ClaimedObjectives(const FWarSiegeState& S)
{
    if (S.Phase == EWarSiegePhase::Waiting) return 0;
    if (S.RulesVersion >= 2) return uint16(S.MainClaims | ((S.OptionalClaims & 7u) << 8));
    // Milestones survive a defender victory and reset only when a new round starts.
    const int32 Count = FMath::Clamp(S.MilestoneSeconds.Num() + (S.Stage == 2 && S.bAttackersWon ? 1 : 0), 0, 8);
    return uint16(((1u << Count) - 1) | ((S.OptionalClaims & 7u) << 8));
}
bool WarSiege::CenterUnlocked(const FWarSiegeState& S)
{ return S.RulesVersion == 1 ? S.Objective >= 2 : (S.MainClaims & 0x30) == 0x30; }
bool WarSiege::RequiresCrew(const FWarSiegeState& S)
{ return S.Stage < 2 && (IsEscort(S) || (S.Objective == FinalObjective(S.Stage) && (S.Stage == 0 || S.RulesVersion == 1))); }
bool WarSiege::Start(FWarSiegeState& S, int32 Capacity, EWarSiegeScenario Scenario, int32 Version)
{
    if ((Version != 1 && Version != 2) || !ValidCapacity(Capacity) || (Scenario != EWarSiegeScenario::FullSiege && Scenario != EWarSiegeScenario::LowerCity)
        || (Scenario == EWarSiegeScenario::LowerCity && Capacity != 6)
        || S.Phase == EWarSiegePhase::Active || S.Phase == EWarSiegePhase::Transition) return false;
    S = {}; S.RulesVersion = Version; S.Capacity = Capacity; S.Scenario = Scenario; S.Phase = EWarSiegePhase::Active; return true;
}
namespace
{
    void Capture(float& Progress, double& Absence, int32 Attackers, int32 Defenders, double Dt, bool Escort)
    {
        const double PreviousAbsence = Absence;
        Absence = Attackers > 0 ? 0 : Absence + Dt;
        if (Attackers > 0 && Defenders == 0)
            Progress = FMath::Min(1.f, Progress + float(Dt / 90 * WarSiege::ParticipationRate(Attackers, Escort)));
        else if (Attackers == 0 && !Escort)
            Progress = FMath::Max(0.f, Progress - float(.05 * (FMath::Max(0., Absence - 10) - FMath::Max(0., PreviousAbsence - 10))));
    }
    void Finish(FWarSiegeState& S, bool Won)
    { S.Phase = EWarSiegePhase::Finished; S.bAttackersWon = Won; S.Remaining = 0; ++S.ResultCount; }
}
void WarSiege::Tick(FWarSiegeState& S, const FWarSiegePresence& P, double Delta)
{
    if (!FMath::IsFinite(Delta) || Delta <= 0 || !ValidCapacity(S.Capacity)) return;
    // Fixed substeps make timeout/capture ordering independent of server frame rate.
    while (Delta > 0 && S.Phase != EWarSiegePhase::Finished && S.Phase != EWarSiegePhase::Waiting)
    {
        const double Dt = FMath::Min(Delta, .05); Delta -= Dt;
        S.Elapsed += Dt;
        if (S.Phase == EWarSiegePhase::Transition)
        {
            S.Remaining -= Dt;
            if (S.Remaining <= 1.e-6)
            { ++S.Stage; S.Objective = 0; S.Progress = S.OptionalProgress = 0; S.bOptionalComplete = S.bOvertime = false;
              S.Absence = S.OptionalAbsence = S.OvertimeAbsence = 0; S.Remaining = StageSeconds; S.Phase = EWarSiegePhase::Active; return; }
            // Do not apply the previous stage's presence to the next stage.
            continue;
        }
        const bool Activity = S.Objective == FinalObjective(S.Stage)
            && (S.Stage == 2 ? P.bRecentCommanderDamage : P.Attackers > 0 && (!RequiresCrew(S) || P.bCrewAlive));
        if ((P.Attackers > 0 && P.Defenders > 0)
            || (S.Stage == 1 && S.RulesVersion >= 2 && ((P.LeftAttackers > 0 && P.LeftDefenders > 0) || (P.RightAttackers > 0 && P.RightDefenders > 0)))) S.ContestedSeconds += Dt;
        if (!S.bOptionalComplete)
        {
            Capture(S.OptionalProgress, S.OptionalAbsence, P.OptionalAttackers, P.OptionalDefenders, Dt, false);
            S.bOptionalComplete = S.OptionalProgress >= 1;
            if (S.bOptionalComplete) S.OptionalClaims |= 1 << S.Stage;
        }
        if (S.Stage < 2)
        {
            if (S.Stage == 1 && S.RulesVersion >= 2)
            {
                const bool PreviouslyUnlocked = CenterUnlocked(S);
                for (int32 Side = 0; Side < 2; ++Side)
                {
                    const uint8 Claim = 1 << (4 + Side);
                    if (S.MainClaims & Claim) continue;
                    float& Progress = Side == 0 ? S.LeftProgress : S.RightProgress;
                    double& Absence = Side == 0 ? S.LeftAbsence : S.RightAbsence;
                    Capture(Progress, Absence, Side == 0 ? P.LeftAttackers : P.RightAttackers,
                        Side == 0 ? P.LeftDefenders : P.RightDefenders, Dt, false);
                    if (Progress >= 1) { S.MainClaims |= Claim; S.MilestoneSeconds.Add(S.Elapsed); }
                }
                S.Objective = CenterUnlocked(S) ? 2 : ((S.MainClaims & 0x10) ? 1 : 0);
                // Presence sampled while the plaza was locked cannot advance it in this tick.
                if (!PreviouslyUnlocked && CenterUnlocked(S)) return;
                if (!CenterUnlocked(S)) { S.Progress = 0; S.Absence = 0; }
                else Capture(S.Progress, S.Absence, P.Attackers, P.Defenders, Dt, false);
            }
            else if (!RequiresCrew(S) || P.bCrewAlive) Capture(S.Progress, S.Absence, P.Attackers, P.Defenders, Dt, IsEscort(S));
            if (IsEscort(S) && !P.bEscortAtCheckpoint) S.Progress = FMath::Min(S.Progress, .99f);
            if (S.Progress >= 1)
            {
                S.MainClaims |= 1 << (S.Stage == 0 ? S.Objective : 4 + S.Objective);
                S.MilestoneSeconds.Add(S.Elapsed);
                if (S.Objective == FinalObjective(S.Stage))
                {
                    if (S.Scenario == EWarSiegeScenario::LowerCity) Finish(S, true);
                    else { S.Phase = EWarSiegePhase::Transition; S.Remaining = TransitionSeconds; S.bOvertime = false; }
                }
                else { ++S.Objective; S.Progress = 0; S.Absence = 0; }
                return;
            }
        }
        else if (P.bCommanderDead) { S.MainClaims |= 0x80; Finish(S, true); return; }
        S.Remaining -= Dt;
        if (S.bOvertime)
        {
            S.OvertimeAbsence = Activity ? 0 : S.OvertimeAbsence + Dt;
            if (S.Remaining <= 1.e-6 || S.OvertimeAbsence >= 10) Finish(S, false);
        }
        else if (S.Remaining <= 1.e-6)
        {
            if (Activity) { S.bOvertime = true; S.Remaining = OvertimeSeconds; S.OvertimeAbsence = 0; }
            else Finish(S, false);
        }
    }
}
EWarSiegeRole WarSiege::MissingRole(int32 Capacity, int32 Tanks, int32 Healers)
{
    if (Tanks < Capacity / 6) return EWarSiegeRole::Tank;
    if (Healers < Capacity / 6) return EWarSiegeRole::Healer;
    return EWarSiegeRole::Damage;
}
EWarSiegeDecision WarSiege::Decide(bool Hazard, bool Recovering, float Hp, bool Threat, bool Objective, bool Leader)
{
    if (Hazard) return EWarSiegeDecision::Evade;
    if (Hp < .25f || (Recovering && Hp < .6f)) return EWarSiegeDecision::Recover;
    if (Threat) return EWarSiegeDecision::Combat;
    if (Objective || !Leader) return EWarSiegeDecision::Objective;
    return EWarSiegeDecision::Follow;
}
